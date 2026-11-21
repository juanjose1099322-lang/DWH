#!/usr/bin/env python3
"""
JOB 3a · COMBINER / REDUCER — promedio de coordenadas por código postal.

El promedio no es asociativo, pero (Σlat, Σlng, n) sí: el combiner suma parciales y el
reducer divide al final, así el resultado es exacto aunque haya varios mappers.
Combiner: zip \t Σlat \t Σlng \t n      Reducer: zip \t lat \t lng \t n_puntos
"""
import sys
from itertools import groupby

COMBINER = "--combiner" in sys.argv


def registros():
    for linea in sys.stdin:
        p = linea.rstrip("\n").split("\t")
        if len(p) == 4:
            yield p[0], float(p[1]), float(p[2]), int(p[3])


for zip_, grupo in groupby(registros(), key=lambda r: r[0]):
    sl = sg = 0.0
    n = 0
    for _, a, b, c in grupo:
        sl, sg, n = sl + a, sg + b, n + c
    if COMBINER:
        print(f"{zip_}\t{sl}\t{sg}\t{n}")
    else:
        print(f"{zip_}\t{sl / n:.6f}\t{sg / n:.6f}\t{n}")
