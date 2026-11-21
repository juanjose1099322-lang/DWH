#!/usr/bin/env python3
"""
JOB 1 · MAPPER — Frecuencia de términos por clase de sentimiento (modelo Naive Bayes).

Entrada : resenas.tsv  ->  R \t review_id \t order_id \t score \t fecha \t texto
Salida  : termino \t clase \t 1        (clase = NEG 1-2★, NEU 3★, POS 4-5★)
          __DOCS__ \t clase \t 1       (conteo de documentos por clase = probabilidad a priori)

Solo procesa el 80 % de entrenamiento; el 20 % de prueba lo clasifica el Job 4.
"""
import os
import sys
sys.path.insert(0, ".")
from texto_pt import normalizar, terminos, clase, es_prueba

for linea in sys.stdin:
    p = linea.rstrip("\n").split("\t")
    if len(p) != 6 or p[0] != "R" or not p[3].isdigit():
        print("reporter:counter:Job1,RegistrosInvalidos,1", file=sys.stderr)
        continue
    if es_prueba(p[1]) and os.getenv("MR_TODO") != "1":   # MR_TODO=1 solo en el benchmark
        continue
    c = clase(int(p[3]))
    print(f"__DOCS__\t{c}\t1")
    for t in terminos(normalizar(p[5])):
        print(f"{t}\t{c}\t1")
    print("reporter:counter:Job1,ResenasEntrenamiento,1", file=sys.stderr)
