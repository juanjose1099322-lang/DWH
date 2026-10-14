"""
Genera dashboard/data.json con los indicadores del tablero gerencial,
precalculados para cada combinación de filtros (Año × Región del cliente).
Las cifras salen de la vista vw_cubo_base (capa ROLAP).
"""
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_olist import DW_URL, ROOT

con = duckdb.connect(DW_URL.replace("duckdb:///", "", 1), read_only=True)
q = lambda sql: con.execute(sql).fetchall()

ANIOS = ["Todos", "2017", "2018"]
REGIONES = ["Todas", "Sudeste", "Sur", "Nordeste", "Centro-Oeste", "Norte"]

def filtro(anio, region, alias=""):
    w = ["grupo_estado <> 'Cancelado'"]
    if anio != "Todos":
        w.append(f"anio = {anio}")
    if region != "Todas":
        w.append(f"region_cliente = '{region}'")
    return " AND ".join(w)

out = {"anios": ANIOS, "regiones": REGIONES, "cortes": {}}
for a in ANIOS:
    for r in REGIONES:
        W = filtro(a, r)
        WD = W + " AND estado_pedido = 'delivered' AND dias_entrega IS NOT NULL"
        k = q(f"""SELECT SUM(ingreso_neto), COUNT(DISTINCT order_id),
                         SUM(ingreso_bruto)/COUNT(DISTINCT order_id),
                         100.0*SUM(flete)/SUM(ingreso_neto),
                         COUNT(DISTINCT customer_unique_id)
                  FROM vw_cubo_base WHERE {W}""")[0]
        kd = q(f"""SELECT 100.0*AVG(es_tardio), AVG(dias_entrega), AVG(calificacion)
                   FROM vw_cubo_base WHERE {WD}""")[0]
        # % de clientes que compran más de una vez
        rec = q(f"""SELECT 100.0*AVG(CASE WHEN n>1 THEN 1 ELSE 0 END) FROM (
                      SELECT customer_unique_id, COUNT(DISTINCT order_id) n
                      FROM vw_cubo_base WHERE {W} GROUP BY 1)""")[0][0]
        mensual = q(f"""SELECT anio_mes, SUM(ingreso_neto), COUNT(DISTINCT order_id)
                        FROM vw_cubo_base WHERE {W} AND anio_mes BETWEEN '2017-01' AND '2018-08'
                        GROUP BY 1 ORDER BY 1""")
        cats = q(f"""SELECT categoria, SUM(ingreso_neto), COUNT(DISTINCT order_id)
                     FROM vw_cubo_base WHERE {W} GROUP BY 1 ORDER BY 2 DESC LIMIT 10""")
        estados = q(f"""SELECT estado_cliente, COUNT(DISTINCT order_id),
                               SUM(ingreso_bruto)/COUNT(DISTINCT order_id),
                               100.0*SUM(flete)/SUM(ingreso_neto)
                        FROM vw_cubo_base WHERE {W} GROUP BY 1 ORDER BY 2 DESC""")
        rutas = q(f"""SELECT estado_vendedor || ' → ' || estado_cliente, COUNT(DISTINCT order_id),
                             AVG(dias_entrega), 100.0*AVG(es_tardio), AVG(calificacion)
                      FROM vw_cubo_base WHERE {WD} GROUP BY 1
                      HAVING COUNT(DISTINCT order_id) >= 50 ORDER BY 4 DESC LIMIT 8""")
        retraso = q(f"""SELECT CASE WHEN dias_retraso <= -10 THEN '1|10+ días antes'
                                    WHEN dias_retraso <= -1 THEN '2|1-9 días antes'
                                    WHEN dias_retraso = 0  THEN '3|El día estimado'
                                    WHEN dias_retraso <= 3 THEN '4|1-3 días tarde'
                                    WHEN dias_retraso <= 7 THEN '5|4-7 días tarde'
                                    ELSE '6|8+ días tarde' END b,
                               AVG(calificacion), COUNT(DISTINCT order_id)
                        FROM vw_cubo_base WHERE {WD} AND calificacion IS NOT NULL
                        GROUP BY 1 ORDER BY 1""")
        pagos = q(f"""SELECT tipo_pago, COUNT(DISTINCT order_id), AVG(calificacion)
                      FROM vw_cubo_base WHERE {W} AND tipo_pago <> 'No definido'
                      GROUP BY 1 ORDER BY 2 DESC""")
        cuotas = q(f"""SELECT rango_valor_compra,
                         100.0*COUNT(DISTINCT CASE WHEN rango_cuotas IN ('4-6','7+') THEN order_id END)
                              / COUNT(DISTINCT order_id)
                       FROM vw_cubo_base WHERE {W} GROUP BY 1 ORDER BY 1""")
        R = lambda x, n=1: None if x is None else round(float(x), n)
        out["cortes"][f"{a}|{r}"] = {
            "kpi": {"ingreso": R(k[0], 0), "pedidos": k[1], "ticket": R(k[2], 2),
                    "flete_pct": R(k[3]), "clientes": k[4], "recompra_pct": R(rec),
                    "tardios_pct": R(kd[0]), "dias_entrega": R(kd[1]), "calificacion": R(kd[2], 2)},
            "mensual": [[m, R(v, 0), p] for m, v, p in mensual],
            "categorias": [[c, R(v, 0), p] for c, v, p in cats],
            "estados": [[e, p, R(t, 2), R(f)] for e, p, t, f in estados],
            "rutas": [[ru, p, R(d), R(t), R(c, 2)] for ru, p, d, t, c in rutas],
            "retraso": [[b.split("|")[1], R(c, 2), p] for b, c, p in retraso],
            "pagos": [[t, p, R(c, 2)] for t, p, c in pagos],
            "cuotas_por_valor": [[v[3:], R(p)] for v, p in cuotas],
        }

destino = ROOT / "dashboard" / "data.json"
destino.parent.mkdir(exist_ok=True)
destino.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"OK {destino} ({destino.stat().st_size/1024:.0f} KB)")


# Construye el tablero: plantilla + datos embebidos (un solo archivo, sin servidor)
plantilla = (ROOT / "dashboard" / "plantilla.html").read_text(encoding="utf-8")
fragmento = plantilla.replace("__DATA__", destino.read_text(encoding="utf-8"))
(ROOT / "dashboard" / "tablero_fragmento.html").write_text(fragmento, encoding="utf-8")
(ROOT / "dashboard" / "index.html").write_text(
    '<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>\n'
    + fragmento + "\n</body></html>\n", encoding="utf-8")
print("OK dashboard/index.html")
