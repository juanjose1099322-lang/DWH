#!/usr/bin/env python3
"""
Emulador local de Hadoop Streaming (para validar la lógica antes de ir al clúster).

Reproduce las fases de un job MapReduce con los MISMOS scripts que corren en YARN:
  1. Input split   : parte cada archivo de entrada en N bloques (como los bloques de HDFS)
  2. Map           : un proceso mapper por bloque, en paralelo
  3. Combine       : sort + combiner sobre la salida de cada mapper (lado del mapper)
  4. Shuffle/Sort  : mezcla ordenada por clave de todas las salidas (sort -m)
  5. Reduce        : el reducer recibe las claves agrupadas
  -files           : los archivos auxiliares se copian al directorio de trabajo del task
  Contadores       : lee las líneas reporter:counter: que los scripts escriben en stderr

Uso:  python mapreduce/run_local.py            (deja las salidas en data/mr_out/)
En el clúster se usa mapreduce/run_hadoop.sh, que ejecuta exactamente los mismos scripts.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "mapreduce"
IN = ROOT / "data" / "hdfs_in"
OUT = ROOT / "data" / "mr_out"
N_MAPS = int(os.getenv("N_MAPS", "4"))
ENV = {**os.environ, "LC_ALL": "C"}
RE_CNT = re.compile(r"^reporter:counter:([^,]+),([^,]+),(\d+)$")


def partir(archivo: Path, n: int, dst: Path):
    """Divide en n bloques respetando límites de línea (TextInputFormat)."""
    lineas = archivo.read_text(encoding="utf-8").splitlines(keepends=True)
    paso = -(-len(lineas) // n)
    bloques = []
    for i in range(n):
        b = dst / f"{archivo.stem}.split{i}"
        b.write_text("".join(lineas[i * paso:(i + 1) * paso]), encoding="utf-8")
        bloques.append(b)
    return bloques


def job(nombre, entradas, mapper, reducer, combiner=None, files=(), salida=None):
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix=f"{nombre}_"))
    for f in ["texto_pt.py", mapper, reducer, combiner, *files]:
        if f and not f.startswith("cat"):
            f = f.split(" ")[0]
            shutil.copy(MR / f, tmp / f)
    bloques = [b for e in entradas for b in partir(e, N_MAPS, tmp)]
    contadores = Counter()

    def cmd(s):
        return s if s.startswith("cat") else f"python3 {s}"

    def correr_map(i, bloque):
        etapa = f"{cmd(mapper)} < {bloque.name} | sort -t$'\\t' -k1,1"
        if combiner:
            etapa += f" | {cmd(combiner)}"
        r = subprocess.run(["bash", "-c", f"{etapa} > map_{i}.out"], cwd=tmp, env=ENV,
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"[{nombre}] fallo en map {i}: {r.stderr[-800:]}")
        return r.stderr

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as ex:
        errs = list(ex.map(lambda a: correr_map(*a), enumerate(bloques)))
    t_map = time.time() - t0
    salida = salida or OUT / nombre
    shutil.rmtree(salida, ignore_errors=True)
    salida.mkdir(parents=True)
    r = subprocess.run(["bash", "-c",
                        f"sort -m -t$'\\t' -k1,1 map_*.out | {cmd(reducer)} > {salida}/part-00000"],
                       cwd=tmp, env=ENV, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"[{nombre}] fallo en reduce: {r.stderr[-800:]}")
    for e in errs + [r.stderr]:
        for linea in e.splitlines():
            m = RE_CNT.match(linea)
            if m:
                contadores[f"{m[1]}.{m[2]}"] += int(m[3])
    reg_in = sum(1 for e in entradas for _ in open(e, encoding="utf-8"))
    reg_map = sum(sum(1 for _ in open(tmp / f"map_{i}.out")) for i in range(len(bloques)))
    reg_out = sum(1 for _ in open(salida / "part-00000", encoding="utf-8"))
    (salida / "_SUCCESS").touch()
    shutil.rmtree(tmp)
    info = {"job": nombre, "maps": len(bloques), "registros_entrada": reg_in,
            "registros_tras_combiner": reg_map, "registros_salida": reg_out,
            "seg_map": round(t_map, 2), "seg_total": round(time.time() - t0, 2),
            "contadores": dict(contadores)}
    print(f"{nombre:<16} maps={len(bloques):<3} in={reg_in:>9,}  map+comb={reg_map:>9,}  "
          f"out={reg_out:>7,}  {info['seg_total']:>6.2f}s  {dict(contadores)}")
    return info


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    log = []
    log.append(job("job1_terminos", [IN / "resenas.tsv"], "job1_mapper.py",
                   "job1_reducer.py", combiner="job1_reducer.py --combiner"))
    shutil.copy(OUT / "job1_terminos" / "part-00000", MR / "modelo_nb.tsv")
    log.append(job("job2a_join", [IN / "resenas.tsv", IN / "entregas.tsv"],
                   "job2_mapper.py", "job2_reducer.py"))
    log.append(job("job2b_temas", [OUT / "job2a_join" / "part-00000"], "cat", "job2b_reducer.py"))
    log.append(job("job3a_centroides", [IN / "geolocalizacion.csv"], "job3a_mapper.py",
                   "job3a_reducer.py", combiner="job3a_reducer.py --combiner"))
    shutil.copy(OUT / "job3a_centroides" / "part-00000", MR / "centroides.tsv")
    log.append(job("job3b_distancias", [IN / "entregas.tsv"], "job3b_mapper.py",
                   "job3b_reducer.py", combiner="job3b_reducer.py --combiner",
                   files=["centroides.tsv"]))
    log.append(job("job4_clasificar", [IN / "resenas.tsv"], "job4_mapper.py",
                   "job4_reducer.py", files=["modelo_nb.tsv"]))
    for f in ("modelo_nb.tsv", "centroides.tsv"):
        (MR / f).unlink(missing_ok=True)
    (OUT / "_bitacora_local.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"Total: {sum(j['seg_total'] for j in log):.1f} s")
