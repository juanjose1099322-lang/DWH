"""
Verifica que las salidas de MapReduce (data/mr_out/) coincidan con la ejecución de referencia
(mapreduce/esperado.json). Sirve para demostrar que el clúster Hadoop y el emulador local
producen los mismos resultados con los mismos scripts.

  python mapreduce/verificar_salidas.py            -> compara
  python mapreduce/verificar_salidas.py --generar  -> crea esperado.json desde data/mr_out/
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "mr_out"
REF = ROOT / "mapreduce" / "esperado.json"
JOBS = ["job1_terminos", "job2a_join", "job2b_temas", "job3a_centroides",
        "job3b_distancias", "job4_clasificar"]


def huella(job):
    filas = [l.rstrip("\n").split("\t") for p in sorted((OUT / job).glob("part-*"))
             for l in open(p, encoding="utf-8") if l.strip()]
    sumas = {}
    for f in filas:
        for i, v in enumerate(f):
            try:
                sumas[i] = sumas.get(i, 0.0) + float(v)
            except ValueError:
                pass
    claves = sorted("|".join(f[:2]) for f in filas)
    return {"filas": len(filas), "sumas": {str(k): round(v, 3) for k, v in sumas.items()},
            "claves_muestra": claves[:3] + claves[-3:]}


if "--generar" in sys.argv:
    REF.write_text(json.dumps({j: huella(j) for j in JOBS}, indent=1, ensure_ascii=False))
    sys.exit(f"Referencia guardada en {REF}")

ref = json.loads(REF.read_text())
ok_total = True
for j in JOBS:
    h, e = huella(j), ref[j]
    ok = h["filas"] == e["filas"] and all(
        abs(h["sumas"].get(k, 0) - v) <= max(1e-6 * abs(v), 0.01) for k, v in e["sumas"].items())
    ok_total &= ok
    print(f"{'OK   ' if ok else 'DIFERENTE'} {j:<18} filas={h['filas']:>7,} (esperado {e['filas']:,})")
print("Todas las salidas coinciden con la referencia." if ok_total else "Hay diferencias: revisar logs.")
sys.exit(0 if ok_total else 1)
