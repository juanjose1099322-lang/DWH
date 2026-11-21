#!/usr/bin/env python3
"""
JOB 1 · COMBINER / REDUCER — suma los conteos de cada término por clase.

Como combiner (--combiner) reemite  termino \t clase \t n  (agrega en el nodo del mapper
y reduce el volumen del shuffle). Como reducer emite una fila por término:
    termino \t n_NEG \t n_NEU \t n_POS \t total
y descarta términos con menos de MIN_SOPORTE documentos (ruido, errores de digitación).
"""
import sys
from itertools import groupby

MIN_SOPORTE = 5
COMBINER = "--combiner" in sys.argv
CLASES = ("NEG", "NEU", "POS")


def registros():
    for linea in sys.stdin:
        p = linea.rstrip("\n").split("\t")
        if len(p) == 3:
            yield p[0], p[1], int(p[2])


for termino, grupo in groupby(registros(), key=lambda r: r[0]):
    cuenta = dict.fromkeys(CLASES, 0)
    for _, c, n in grupo:
        cuenta[c] += n
    if COMBINER:
        for c in CLASES:
            if cuenta[c]:
                print(f"{termino}\t{c}\t{cuenta[c]}")
        continue
    total = sum(cuenta.values())
    if total >= MIN_SOPORTE or termino == "__DOCS__":
        print("\t".join([termino] + [str(cuenta[c]) for c in CLASES] + [str(total)]))
