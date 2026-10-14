"""Exporta las 7 tablas de la estrella a CSV (UTF-8, separador coma) para Power BI."""
import sys
from pathlib import Path
import duckdb
sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_olist import DW_URL, ROOT, ORDEN

destino = ROOT / "powerbi" / "csv"
destino.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(DW_URL.replace("duckdb:///", "", 1), read_only=True)
for t in ORDEN:
    con.execute(f"COPY {t} TO '{destino / (t + '.csv')}' (HEADER, DELIMITER ',')")
    print(f"OK {t}.csv")
