"""
Contraste de rendimiento: motor de la bodega (DuckDB, SQL) vs. MapReduce (Hadoop Streaming).

Se resuelven DOS tareas del Corte 3 con ambos enfoques y con el volumen real (×1) y
volúmenes simulados (×5, ×20) obtenidos replicando los archivos de entrada:
  T1 · Minería de texto: frecuencia de unigramas y bigramas por clase de sentimiento (Job 1)
  T2 · Centroides de 1 millón de puntos de geolocalización (Job 3a)

Para MapReduce se usa el emulador local (mismos scripts, una sola máquina de 2 núcleos):
mide el costo del paradigma sin la ventaja de un clúster. Los tiempos sobre YARN se toman
de evidencias/tiempos_yarn.tsv. Uso: python mapreduce/benchmark_dw_vs_mr.py
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mapreduce"))
import run_local  # noqa: E402
from texto_pt import STOPWORDS  # noqa: E402

IN = ROOT / "data" / "hdfs_in"
TMP = ROOT / "data" / "bench"
FACTORES = [int(x) for x in os.getenv("FACTORES", "1,5,20").split(",")]

SQL_T1 = """
WITH base AS (
  SELECT CASE WHEN score <= 2 THEN 'NEG' WHEN score = 3 THEN 'NEU' ELSE 'POS' END AS clase,
         trim(regexp_replace(regexp_replace(strip_accents(lower(texto)), '[^a-z0-9\\s-]', ' ', 'g'),
                             '\\s+', ' ', 'g')) AS t, review_id
  FROM read_csv('{f}', delim='\\t', header=false, quote='', escape='',
                columns={{'tag':'VARCHAR','review_id':'VARCHAR','order_id':'VARCHAR',
                          'score':'INTEGER','fecha':'VARCHAR','texto':'VARCHAR'}})
  ),
tok AS (
  SELECT clase, list_filter(string_split(t, ' '),
           lambda x: length(x) >= 2 AND NOT list_contains({stop}, x)
                AND NOT regexp_full_match(x, '[0-9]+')) AS k
  FROM base ),
terms AS (
  SELECT clase, unnest(list_distinct(list_concat(k,
           list_transform(range(1, length(k)), lambda i: k[i] || '_' || k[i + 1])))) AS termino
  FROM tok )
SELECT termino, count(*) FILTER (clase = 'NEG') n, count(*) FILTER (clase = 'NEU') u,
       count(*) FILTER (clase = 'POS') p, count(*) total
FROM terms GROUP BY termino HAVING count(*) >= 5
"""

SQL_T2 = """
SELECT lpad(CAST(column0 AS VARCHAR), 5, '0') AS cep, avg(column1) lat, avg(column2) lng, count(*) n
FROM read_csv('{f}', header=true, columns={{'column0':'VARCHAR','column1':'DOUBLE','column2':'DOUBLE',
                                            'column3':'VARCHAR','column4':'VARCHAR'}})
WHERE column1 BETWEEN -34 AND 5.5 AND column2 BETWEEN -74 AND -34.5
GROUP BY 1
"""


def replicar(src: Path, k: int, dst: Path, cabecera=False):
    with open(src, encoding="utf-8") as f:
        lineas = f.readlines()
    head, cuerpo = (lineas[:1], lineas[1:]) if cabecera else ([], lineas)
    with open(dst, "w", encoding="utf-8") as out:
        out.writelines(head)
        for i in range(k):
            for l in cuerpo:
                # se altera el id para que cada copia sea una reseña distinta
                out.write(l[:2] + f"{i:02d}" + l[2:] if i and not cabecera else l)
    return dst


def cronometrar(fn):
    t0 = time.time()
    r = fn()
    return round(time.time() - t0, 2), r


if __name__ == "__main__":
    TMP.mkdir(parents=True, exist_ok=True)
    stop = "[" + ",".join(f"'{w}'" for w in sorted(STOPWORDS)) + "]"
    res = []
    for k in FACTORES:
        fr = replicar(IN / "resenas.tsv", k, TMP / f"resenas_x{k}.tsv")
        fg = replicar(IN / "geolocalizacion.csv", k, TMP / f"geo_x{k}.csv", cabecera=True)
        mb_r, mb_g = fr.stat().st_size / 2**20, fg.stat().st_size / 2**20
        con = duckdb.connect()
        # T1: el SQL procesa el 100 %; para comparar igual, MR también (se desactiva el 80/20)
        t_sql1, n_sql1 = cronometrar(lambda: con.execute(SQL_T1.format(f=fr, stop=stop)).fetchall())
        t_sql2, n_sql2 = cronometrar(lambda: con.execute(SQL_T2.format(f=fg)).fetchall())
        run_local.N_MAPS = 2
        run_local.ENV["MR_TODO"] = "1"
        j1 = run_local.job("bench_t1", [fr], "job1_mapper.py", "job1_reducer.py",
                           combiner="job1_reducer.py --combiner", salida=TMP / "o1")
        j2 = run_local.job("bench_t2", [fg], "job3a_mapper.py", "job3a_reducer.py",
                           combiner="job3a_reducer.py --combiner", salida=TMP / "o2")
        res.append({"factor": k, "resenas_mb": round(mb_r, 1), "geo_mb": round(mb_g, 1),
                    "filas_resenas": 42687 * k, "filas_geo": 1000163 * k,
                    "t1_sql_s": t_sql1, "t1_mr_s": j1["seg_total"], "t1_terminos_sql": len(n_sql1),
                    "t1_terminos_mr": j1["registros_salida"] - 1,
                    "t2_sql_s": t_sql2, "t2_mr_s": j2["seg_total"], "t2_ceps_sql": len(n_sql2),
                    "t2_ceps_mr": j2["registros_salida"]})
        print(res[-1])
        for f in (fr, fg):
            f.unlink()
    (ROOT / "evidencias").mkdir(exist_ok=True)
    (ROOT / "evidencias" / "benchmark_dw_vs_mr.json").write_text(json.dumps(res, indent=1))
    shutil.rmtree(TMP, ignore_errors=True)
