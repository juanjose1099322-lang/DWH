#!/usr/bin/env bash
# Se ejecuta en segundo plano al abrir el escenario: clona el repositorio, instala Hadoop,
# reconstruye la bodega (DuckDB) y prepara los insumos para HDFS. Bitácora en /root/setup.log
REPO_URL="https://github.com/juanjose1099322-lang/DWH.git"
{
  cd /root
  git clone -q "$REPO_URL" olist-dw-bigdata
  cd olist-dw-bigdata
  bash scripts/setup_hadoop.sh
  apt-get install -y -qq python3-venv >/dev/null
  python3 -m venv .venv && . .venv/bin/activate
  pip install -q -r requirements.txt
  cp -n config/.env.example config/.env
  python etl/etl_olist.py
  python etl/ejecutar_sql.py sql/02_cubos_rolap.sql
  python mapreduce/preparar_insumos.py
} > /root/setup.log 2>&1
touch /root/.setup_ok
