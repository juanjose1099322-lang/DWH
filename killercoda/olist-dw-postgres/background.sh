#!/usr/bin/env bash
# Se ejecuta en segundo plano al abrir el escenario (antes del paso 1).
# Cambia REPO_URL por la URL del repositorio del equipo en GitHub.
REPO_URL="https://github.com/juanjose1099322-lang/DWH.git"

cd /root
git clone -q "$REPO_URL" olist-dw-bigdata
cd olist-dw-bigdata
bash scripts/setup_postgres.sh > /root/setup.log 2>&1
python3 -m venv .venv && . .venv/bin/activate
pip install -q -r requirements.txt >> /root/setup.log 2>&1
cp config/.env.example config/.env
sed -i 's|^DW_URL=duckdb|# DW_URL=duckdb|; s|^# DW_URL=postgresql|DW_URL=postgresql|' config/.env
touch /root/.setup_ok
