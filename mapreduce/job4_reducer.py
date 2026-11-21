#!/usr/bin/env python3
"""
JOB 4 · REDUCER — matriz de confusión (clase_real × clase_predicha).
Salida : clase_real \t clase_predicha \t n
"""
import sys
from collections import Counter

c = Counter()
for linea in sys.stdin:
    real, pred, n = linea.rstrip("\n").split("\t")
    c[(real, pred)] += int(n)
for (real, pred), n in sorted(c.items()):
    print(f"{real}\t{pred}\t{n}")
