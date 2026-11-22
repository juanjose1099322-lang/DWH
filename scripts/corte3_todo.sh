#!/usr/bin/env bash
# ---------------------------------------------------------------------------------
# Corte 3 en un solo comando (Killercoda / Ubuntu / WSL, como root):
#   bash scripts/corte3_todo.sh
# Instala lo que falte, reconstruye la bodega, instala Hadoop si no está, corre los
# 6 jobs en YARN, integra los resultados con la bodega y regenera el tablero.
# Se puede volver a ejecutar sin problema: salta lo que ya está hecho.
# ---------------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== [1/6] Paquetes del sistema"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl python3-venv python3-full bsdextrautils >/dev/null

echo "=== [2/6] Entorno de Python"
# En Ubuntu (Killercoda/WSL) se usa un entorno virtual; en Google Colab no hace falta
# (y venv falla por la versión de Python), así que se instala directo con pip.
if [ -d /content ] || [ -n "${COLAB_RELEASE_TAG:-}" ]; then
  rm -rf .venv
  pip install -q -r requirements.txt
else
  [ -x .venv/bin/python ] || { rm -rf .venv; python3 -m venv .venv; }
  . .venv/bin/activate
  pip install -q -r requirements.txt
fi
[ -f config/.env ] || cp config/.env.example config/.env

echo "=== [3/6] Bodega de datos (Cortes 1 y 2)"
if [ ! -f data/olist_dw.duckdb ]; then
  python etl/etl_olist.py
fi
python etl/ejecutar_sql.py sql/02_cubos_rolap.sql
python mapreduce/preparar_insumos.py

echo "=== [4/6] Hadoop (HDFS + YARN)"
if [ ! -x /opt/hadoop/bin/hadoop ] || ! jps 2>/dev/null | grep -q NameNode; then
  bash scripts/setup_hadoop.sh
fi
. /etc/profile.d/hadoop.sh
jps | grep -v Jps

echo "=== [5/6] Jobs MapReduce en YARN"
bash mapreduce/run_hadoop.sh

echo "=== [6/6] Integración con la bodega y el tablero"
python mapreduce/cargar_resultados_dw.py
python etl/exportar_dashboard.py

echo
echo "LISTO. Ahora toma las capturas: puertos 9870 (HDFS) y 8088 (YARN) en Traffic / Ports."
