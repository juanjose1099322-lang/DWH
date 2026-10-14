#!/usr/bin/env bash
# ---------------------------------------------------------------------
# Instala PostgreSQL en Ubuntu (Killercoda o local), crea el usuario y la
# base de la bodega y deja el servicio escuchando SOLO en localhost:5432.
# Uso:  bash scripts/setup_postgres.sh
# ---------------------------------------------------------------------
set -euo pipefail

if ! command -v psql >/dev/null 2>&1; then
  echo ">> Instalando PostgreSQL..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-contrib python3-pip python3-venv >/dev/null
fi

sudo service postgresql start

echo ">> Creando usuario dw_user y base olist_dw (idempotente)..."
sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dw_user') THEN
    CREATE ROLE dw_user LOGIN PASSWORD 'dw_pass';
  END IF;
END $$;
SQL
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='olist_dw'" | grep -q 1 \
  || sudo -u postgres createdb -O dw_user olist_dw

echo ">> Verificando conexión con la cadena estándar local..."
PGPASSWORD=dw_pass psql "host=localhost port=5432 dbname=olist_dw user=dw_user" -tAc "SELECT 'conexion OK: ' || version();"
