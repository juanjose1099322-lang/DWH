"""
Ejecuta un archivo .sql contra la bodega indicada por DW_URL y muestra los
resultados de cada SELECT. Funciona igual con DuckDB y PostgreSQL.

Uso:
    python etl/ejecutar_sql.py sql/02_cubos_rolap.sql
    python etl/ejecutar_sql.py sql/03_operaciones_olap.sql
"""
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etl_olist import DW_URL  # reutiliza la misma configuración (config/.env)

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)


def sentencias(ruta):
    texto = Path(ruta).read_text(encoding="utf-8")
    sin_comentarios = "\n".join(re.sub(r"--.*$", "", l) for l in texto.splitlines())
    return [s.strip() for s in sin_comentarios.split(";") if s.strip()]


def conectar():
    if DW_URL.startswith("duckdb://"):
        import duckdb
        con = duckdb.connect(DW_URL.replace("duckdb:///", "", 1))
        return (lambda q: con.execute(q).df() if q.lstrip().upper().startswith(("SELECT", "WITH"))
                else con.execute(q)), con.close
    from sqlalchemy import create_engine, text
    eng = create_engine(DW_URL)
    cx = eng.connect()
    def run(q):
        if q.lstrip().upper().startswith(("SELECT", "WITH")):
            return pd.read_sql(text(q), cx)
        cx.execute(text(q)); cx.commit()
    return run, cx.close


if __name__ == "__main__":
    run, cerrar = conectar()
    for i, q in enumerate(sentencias(sys.argv[1]), 1):
        res = run(q)
        if isinstance(res, pd.DataFrame):
            print(f"\n--- Consulta {i} ({len(res)} filas) ---")
            print(res.to_string(index=False))
    cerrar()
    print(f"\nOK: {sys.argv[1]} ejecutado en {DW_URL.split('://')[0]}")
