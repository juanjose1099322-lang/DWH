"""
Prepara los insumos que se suben a HDFS para el Corte 3.

  1. resenas.tsv     <- olist_order_reviews_dataset.csv (CRUDO, texto libre en portugués)
                        El CSV trae saltos de línea dentro de los comentarios; Hadoop parte
                        los archivos por línea, así que cada reseña se deja en UNA sola línea.
                        No se limpia ni se tokeniza: eso lo hacen los mappers (schema-on-read).
  2. entregas.tsv    <- exportado desde la BODEGA (fact_order_items + dimensiones), una fila
                        por pedido-vendedor entregado. Es el "offload" DW -> HDFS.
  3. geolocalizacion <- olist_geolocation_dataset.csv se sube tal cual (1.000.163 filas).

Uso:  python mapreduce/preparar_insumos.py   (deja los archivos en data/hdfs_in/)
"""
import csv
import shutil
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "hdfs_in"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "etl"))


def una_linea(s: str) -> str:
    return " ".join((s or "").replace("\t", " ").split())


# 1. Reseñas: registro etiquetado R
n_r = n_txt = 0
with open(RAW / "olist_order_reviews_dataset.csv", encoding="utf-8", newline="") as f, \
     open(OUT / "resenas.tsv", "w", encoding="utf-8") as out:
    for row in csv.DictReader(f):
        n_r += 1
        texto = una_linea(f"{row['review_comment_title']} {row['review_comment_message']}")
        if not texto:
            continue                       # sin texto: no aporta a la minería
        n_txt += 1
        out.write("\t".join(["R", row["review_id"], row["order_id"],
                             row["review_score"], row["review_creation_date"][:10], texto]) + "\n")
print(f"resenas.tsv      {n_txt:>9,} reseñas con texto (de {n_r:,})")

# 2. Entregas desde la bodega: registro etiquetado E
from etl_olist import DW_URL  # noqa: E402
con = duckdb.connect(DW_URL.replace("duckdb:///", "", 1), read_only=True)
filas = con.execute("""
    SELECT f.order_id, s.seller_id, s.seller_zip_prefix, s.seller_state,
           c.customer_zip_prefix, c.customer_state,
           MAX(f.delivery_time_days), MAX(f.delivery_delay_days), MAX(f.is_late_flag),
           MAX(f.review_score), ROUND(SUM(f.price), 2), ROUND(SUM(f.freight_value), 2)
    FROM fact_order_items f
    JOIN dim_seller s       ON s.seller_key = f.seller_key
    JOIN dim_customer c     ON c.customer_key = f.customer_key
    JOIN dim_order_status o ON o.order_status_key = f.order_status_key
    WHERE o.status_name = 'delivered' AND f.delivery_time_days IS NOT NULL
    GROUP BY 1, 2, 3, 4, 5, 6
""").fetchall()
with open(OUT / "entregas.tsv", "w", encoding="utf-8") as out:
    for r in filas:
        out.write("\t".join(["E"] + ["" if v is None else str(v) for v in r]) + "\n")
print(f"entregas.tsv     {len(filas):>9,} pedido-vendedor entregados (desde la bodega)")

# 3. Geolocalización: cruda
shutil.copy(RAW / "olist_geolocation_dataset.csv", OUT / "geolocalizacion.csv")
print(f"geolocalizacion  {sum(1 for _ in open(OUT / 'geolocalizacion.csv')) - 1:>9,} puntos (crudo)")
