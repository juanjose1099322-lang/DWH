#!/usr/bin/env python3
"""
JOB 3b · COMBINER / REDUCER — suma vectorial de las métricas por clave.

Todas las métricas viajan como sumas (n, Σkm, Σdías, ...), que son asociativas; por eso el
mismo código sirve de combiner. El reducer calcula promedios, % de tardíos, flete/precio
y, para la clave GLOBAL, la correlación de Pearson entre distancia y días de entrega.
Reducer: tipo \t clave \t envios \t km_prom \t dias_prom \t pct_tardio \t score_prom
              \t flete_pct \t dias_por_1000km \t r_pearson \t pendiente \t intercepto
(pendiente e intercepto = recta de mínimos cuadrados días = a + b·km, solo en GLOBAL;
 con ella la bodega calcula cuántos días "debería" tardar cada ruta según su distancia)
"""
import math
import sys
from itertools import groupby

COMBINER = "--combiner" in sys.argv


def registros():
    for linea in sys.stdin:
        p = linea.rstrip("\n").split("\t")
        if len(p) == 12:
            yield p[0], [float(x) for x in p[1:]]


for clave, grupo in groupby(registros(), key=lambda r: r[0]):
    S = [0.0] * 11
    for _, v in grupo:
        S = [a + b for a, b in zip(S, v)]
    n, km, d, t, s, ns, km2, d2, kmd, fl, pr = S
    if COMBINER:
        print(clave + "\t" + "\t".join(repr(x) for x in S))
        continue
    r = b = a = ""
    if clave.startswith("GLOBAL"):
        cov, var_km = n * kmd - km * d, n * km2 - km ** 2
        r = f"{cov / math.sqrt(var_km * (n * d2 - d ** 2)):.3f}"
        b = f"{cov / var_km:.6f}"
        a = f"{(d - (cov / var_km) * km) / n:.4f}"
    tipo, nombre = clave.split("|", 1)
    print("\t".join([tipo, nombre, f"{int(n)}", f"{km / n:.1f}", f"{d / n:.2f}",
                     f"{100 * t / n:.2f}", f"{s / ns:.3f}" if ns else "",
                     f"{100 * fl / pr:.2f}", f"{1000 * d / km:.2f}" if km else "", r, b, a]))
