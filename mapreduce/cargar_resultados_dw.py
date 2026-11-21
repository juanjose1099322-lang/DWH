"""
Integración (requerimiento 3 del Corte 3): ingesta las salidas de MapReduce en la bodega.

Lee los part-* de cada job (data/mr_out/<job>/, bajados de HDFS con -getmerge o generados
por run_local.py), los carga como tablas mr_* en el mismo motor de la bodega (DW_URL) y crea
vistas que las cruzan con la estrella. El tablero (etl/exportar_dashboard.py) lee esas tablas,
así que el flujo HDFS -> bodega -> tablero no tiene pasos manuales.

Tablas que crea:
  mr_terminos_sentimiento  término, conteos por clase y log-odds NEG vs POS (minería de texto)
  mr_temas_resenas         temas de queja/elogio y su relación con la entrega tardía
  mr_centroides_cep        coordenadas promedio por prefijo de código postal (19 mil)
  mr_distancia_bandas      desempeño logístico por banda de distancia real
  mr_rutas_distancia       ruta estado->estado con distancia real, días esperados por distancia
                           y exceso de días (enriquece al cubo de logística)
  mr_clasificador_nb       matriz de confusión del clasificador Naive Bayes
  vw_rutas_enriquecidas    vista: mr_rutas_distancia + región de la bodega
"""
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
from etl_olist import DW_URL  # noqa: E402

MR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "mr_out"


def leer(job, columnas):
    partes = sorted((MR / job).glob("part-*"))
    if not partes:
        sys.exit(f"No hay salidas en {MR / job}. Ejecuta primero run_local.py o run_hadoop.sh")
    return pd.concat([pd.read_csv(p, sep="\t", header=None, names=columnas,
                                  keep_default_na=False, dtype=str) for p in partes],
                     ignore_index=True)


# Minería de texto: log-odds con suavizado (Monroe, Colaresi y Quinn, 2008, versión simple)
t = leer("job1_terminos", ["termino", "n_neg", "n_neu", "n_pos", "total"])
for c in ["n_neg", "n_neu", "n_pos", "total"]:
    t[c] = t[c].astype(int)
docs = t[t.termino == "__DOCS__"].iloc[0]
t = t[t.termino != "__DOCS__"].copy()
D_NEG, D_POS = int(docs.n_neg), int(docs.n_pos)
t["log_odds_neg"] = [math.log((n + 1) / (D_NEG - n + 1)) - math.log((p + 1) / (D_POS - p + 1))
                     for n, p in zip(t.n_neg, t.n_pos)]
t["z_neg"] = t.log_odds_neg / [math.sqrt(1 / (n + 1) + 1 / (p + 1)) for n, p in zip(t.n_neg, t.n_pos)]
t["es_bigrama"] = t.termino.str.contains("_")

temas = leer("job2b_temas", ["tema", "resenas", "pct_pedidos_tardios", "score_prom",
                             "score_prom_tarde", "score_prom_a_tiempo", "pct_negativas"])
cent = leer("job3a_centroides", ["cep_prefijo", "lat", "lng", "n_puntos"])
dist = leer("job3b_distancias", ["tipo", "clave", "envios", "km_prom", "dias_prom", "pct_tardio",
                                 "score_prom", "flete_pct", "dias_por_1000km", "r_pearson",
                                 "pendiente", "intercepto"])
conf = leer("job4_clasificar", ["clase_real", "clase_predicha", "n"])

num = lambda df, cols: df.assign(**{c: pd.to_numeric(df[c], errors="coerce") for c in cols})
temas = num(temas, temas.columns[1:])
cent = num(cent, ["lat", "lng", "n_puntos"])
dist = num(dist, dist.columns[2:])
conf = num(conf, ["n"])

bandas = dist[dist.tipo != "RUTA"].copy()
bandas[["orden", "banda"]] = bandas.clave.str.split("|", n=1, expand=True).reindex(columns=[0, 1]).fillna("")
bandas.loc[bandas.tipo == "GLOBAL", ["orden", "banda"]] = ["99", "Total"]
bandas = bandas.drop(columns=["tipo", "clave"])
g = dist[dist.tipo == "GLOBAL"].iloc[0]
rutas = dist[dist.tipo == "RUTA"].drop(columns=["tipo", "r_pearson", "pendiente", "intercepto"]).copy()
# Días esperados según la distancia (recta global del Job 3b) y exceso de cada ruta
rutas["dias_esperados"] = (g.intercepto + g.pendiente * rutas.km_prom).round(2)
rutas["exceso_dias"] = (rutas.dias_prom - rutas.dias_esperados).round(2)
rutas[["estado_vendedor", "estado_cliente"]] = rutas.clave.str.split(">", expand=True)
rutas = rutas.drop(columns=["clave"])

tablas = {"mr_terminos_sentimiento": t, "mr_temas_resenas": temas, "mr_centroides_cep": cent,
          "mr_distancia_bandas": bandas, "mr_rutas_distancia": rutas, "mr_clasificador_nb": conf}

VISTA = """
CREATE VIEW vw_rutas_enriquecidas AS
SELECT r.*, vs.region AS region_vendedor, vc.region AS region_cliente
FROM mr_rutas_distancia r
LEFT JOIN (SELECT DISTINCT seller_state AS estado, seller_region AS region FROM dim_seller) vs
       ON vs.estado = r.estado_vendedor
LEFT JOIN (SELECT DISTINCT customer_state AS estado, customer_region AS region FROM dim_customer) vc
       ON vc.estado = r.estado_cliente
"""

if DW_URL.startswith("duckdb://"):
    import duckdb
    con = duckdb.connect(DW_URL.replace("duckdb:///", "", 1))
    con.execute("DROP VIEW IF EXISTS vw_rutas_enriquecidas")
    for nombre, df in tablas.items():
        con.register("df_tmp", df)
        con.execute(f"CREATE OR REPLACE TABLE {nombre} AS SELECT * FROM df_tmp")
        con.unregister("df_tmp")
    con.execute(VISTA)
    con.close()
else:
    from sqlalchemy import create_engine, text
    eng = create_engine(DW_URL)
    with eng.begin() as cx:
        cx.execute(text("DROP VIEW IF EXISTS vw_rutas_enriquecidas"))
    for nombre, df in tablas.items():
        df.to_sql(nombre, eng, if_exists="replace", index=False)
    with eng.begin() as cx:
        cx.execute(text(VISTA))

for nombre, df in tablas.items():
    print(f"{nombre:<26} {len(df):>7,} filas")
print("vw_rutas_enriquecidas      vista creada")
