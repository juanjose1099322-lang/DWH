# DWH · olist-dw-bigdata

Proyecto de Aula **Data Warehouse y Big Data**, Politécnico Grancolombiano (2026).
Bodega de datos en esquema estrella sobre el *Brazilian E-Commerce Public Dataset by Olist*.

| Corte | Contenido | Estado |
|---|---|---|
| 1 | Contexto, modelo dimensional, diseño ETL | Entregado |
| 2 | ETL implementado, cubos ROLAP, tablero gerencial, laboratorios Colab y Killercoda | Entregado |
| 3 | Hadoop (HDFS + YARN), 6 jobs MapReduce, minería de texto, integración con la bodega y el tablero | Este repositorio |

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

## Corte 3 · MapReduce sobre Hadoop

```
DWH/
├── scripts/setup_hadoop.sh         # Hadoop 3.3.6 pseudo-distribuido (HDFS + YARN) en Ubuntu/Colab
├── mapreduce/
│   ├── preparar_insumos.py         # reseñas (texto crudo) + entregas (desde la bodega) + geolocalización
│   ├── texto_pt.py                 # normalización, stopwords, léxico de temas (se envía con -files)
│   ├── job1_mapper.py / job1_reducer.py     # términos por sentimiento (modelo Naive Bayes)
│   ├── job2_mapper.py / job2_reducer.py     # reduce-side join reseñas ⋈ entregas + temas
│   ├── job2b_reducer.py                     # agregación por tema (mapper = cat)
│   ├── job3a_mapper.py / job3a_reducer.py   # centroides de 1 M de puntos (combiner)
│   ├── job3b_mapper.py / job3b_reducer.py   # map-side join + distancia haversine
│   ├── job4_mapper.py / job4_reducer.py     # clasificador NB + matriz de confusión
│   ├── run_hadoop.sh               # corre todo en YARN y guarda evidencias/
│   ├── run_local.py                # emulador de Hadoop Streaming (validación sin clúster)
│   ├── verificar_salidas.py        # compara las salidas con esperado.json
│   ├── cargar_resultados_dw.py     # salidas MR -> tablas mr_* de la bodega
│   └── benchmark_dw_vs_mr.py       # contraste de rendimiento DuckDB vs MapReduce
├── notebooks/Corte3_MapReduce_Colab.ipynb
├── killercoda/olist-hadoop-mapreduce/
└── evidencias/                     # logs HDFS/YARN, tiempos, benchmark
```

```bash
sudo bash scripts/setup_hadoop.sh && source /etc/profile.d/hadoop.sh
python mapreduce/preparar_insumos.py
bash mapreduce/run_hadoop.sh                 # 6 jobs en YARN + evidencias
python mapreduce/cargar_resultados_dw.py     # integra con la bodega
python etl/exportar_dashboard.py             # tablero con la sección Big Data
```

Sin clúster: `python mapreduce/run_local.py` ejecuta los mismos scripts con el emulador local.
Cadena estándar local de HDFS: `hdfs://localhost:9000` · UIs: NameNode `:9870`, ResourceManager `:8088`, JobHistory `:19888`.

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
