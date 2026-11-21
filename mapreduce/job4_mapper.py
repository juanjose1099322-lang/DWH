#!/usr/bin/env python3
"""
JOB 4 · MAPPER — Clasificador Naive Bayes multinomial sobre el 20 % de prueba.

modelo_nb.tsv (salida del Job 1) viaja con -files. Cada mapper puntúa sus reseñas con
    clase* = argmax_c  log P(c) + Σ_t log P(t | c)      (suavizado de Laplace)
Salida : clase_real \t clase_predicha \t 1
"""
import math
import sys
sys.path.insert(0, ".")
from texto_pt import normalizar, terminos, clase, es_prueba

CLASES = ("NEG", "NEU", "POS")
cuenta, docs = {}, {}
with open("modelo_nb.tsv", encoding="utf-8") as f:
    for linea in f:
        p = linea.rstrip("\n").split("\t")
        valores = list(map(int, p[1:4]))
        if p[0] == "__DOCS__":
            docs = dict(zip(CLASES, valores))
        else:
            cuenta[p[0]] = valores
V = len(cuenta)
tot = [sum(v[i] for v in cuenta.values()) for i in range(3)]
N = sum(docs.values())
prior = [math.log(docs[c] / N) for c in CLASES]
log_den = [math.log(tot[i] + V) for i in range(3)]

for linea in sys.stdin:
    p = linea.rstrip("\n").split("\t")
    if len(p) != 6 or p[0] != "R" or not p[3].isdigit() or not es_prueba(p[1]):
        continue
    puntaje = prior[:]
    for t in terminos(normalizar(p[5])):
        v = cuenta.get(t)
        if v is None:
            continue                      # término fuera del vocabulario
        for i in range(3):
            puntaje[i] += math.log(v[i] + 1) - log_den[i]
    pred = CLASES[max(range(3), key=puntaje.__getitem__)]
    print(f"{clase(int(p[3]))}\t{pred}\t1")
