# DWH · olist-dw-bigdata

Proyecto de Aula **Data Warehouse y Big Data**, Politécnico Grancolombiano (2026).
Bodega de datos en esquema estrella sobre el *Brazilian E-Commerce Public Dataset by Olist*.

| Corte | Contenido | Estado |
|---|---|---|
| 1 | Contexto, modelo dimensional, diseño ETL | Entregado |
| 2 | ETL implementado, cubos ROLAP, tablero gerencial, laboratorios Colab y Killercoda | Este repositorio |
| 3 | Procesamiento distribuido (MapReduce / Spark) | Pendiente |

## Estructura

```
DWH/
├── config/.env.example        # cadenas de conexión estándar locales (copiar a config/.env)
├── etl/
│   ├── etl_olist.py           # Extract → Transform (reglas 1-8) → Load
│   ├── ejecutar_sql.py        # corre cualquier .sql en DuckDB o PostgreSQL
│   ├── exportar_dashboard.py  # genera dashboard/data.json + index.html
│   └── exportar_powerbi.py    # exporta la estrella a CSV para Power BI
├── sql/
│   ├── 01_ddl_estrella.sql    # 6 dimensiones + FACT_ORDER_ITEMS
│   ├── 02_cubos_rolap.sql     # vista base + 4 cubos (CUBE / ROLLUP / GROUPING SETS)
│   └── 03_operaciones_olap.sql# roll-up, drill-down, slice, dice, pivot + preguntas P1-P5
├── notebooks/Corte2_OLAP_Colab.ipynb
├── killercoda/olist-dw-postgres/   # escenario Killercoda (PostgreSQL)
├── dashboard/                 # tablero web (index.html autocontenido)
├── powerbi/GUIA_POWERBI.md    # modelo, medidas DAX y diseño para Power BI
├── scripts/setup_postgres.sh  # instala y configura PostgreSQL en Ubuntu
└── requirements.txt
```

## Ejecución rápida

```bash
pip install -r requirements.txt
cp config/.env.example config/.env           # DuckDB por defecto
python etl/etl_olist.py                      # carga la estrella (≈5 s en DuckDB)
python etl/ejecutar_sql.py sql/02_cubos_rolap.sql
python etl/ejecutar_sql.py sql/03_operaciones_olap.sql
python etl/exportar_dashboard.py             # tablero en dashboard/index.html
```

Para PostgreSQL local: `bash scripts/setup_postgres.sh` y en `config/.env` activa
`DW_URL=postgresql+psycopg2://dw_user:dw_pass@localhost:5432/olist_dw`.

## Cadenas de conexión estándar locales

| Entorno | Motor | DW_URL |
|---|---|---|
| Google Colab / PC | DuckDB embebido | `duckdb:///data/olist_dw.duckdb` |
| Killercoda / Ubuntu | PostgreSQL 5432 | `postgresql+psycopg2://dw_user:dw_pass@localhost:5432/olist_dw` |

El código no tiene hosts ni contraseñas escritos en el programa: todo sale de `config/.env`, que no se versiona.
Como el servidor siempre está en `localhost`, los laboratorios no necesitan reglas de firewall, IP pública ni túneles.
Los CSV se descargan del espejo público oficial de Olist en GitHub, así que no hace falta una cuenta de Kaggle.

## Flujo de trabajo en Git

- `main`: versión estable que se entrega. Cada corte se marca con una etiqueta (`corte-1`, `corte-2`).
- `feature/<tema>`: una rama por tarea (`feature/cubos-rolap`, `feature/dashboard`), que se integra a `main` con un *pull request* revisado por otro integrante.
- Los mensajes de commit van en español e imperativo: `Agrega cubo de logística por rutas`.
- No se versionan los datos (`data/`) ni las credenciales (`config/.env`).

```bash
git checkout -b feature/cubos-rolap
git add sql/02_cubos_rolap.sql && git commit -m "Agrega cubos ROLAP con CUBE y ROLLUP"
git push -u origin feature/cubos-rolap      # abrir PR en GitHub
git tag -a corte-2 -m "Entrega Corte 2" && git push origin corte-2
```

## Fuente

Olist, & Sionek, A. (2018). *Brazilian E-Commerce Public Dataset by Olist* [Data set]. Kaggle.
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
