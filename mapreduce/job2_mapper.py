#!/usr/bin/env python3
"""
JOB 2 · MAPPER — Reduce-side join reseñas ⋈ entregas por order_id + detección de temas.

Entradas (dos fuentes en el mismo job, se distinguen por la etiqueta del registro):
  R \t review_id \t order_id \t score \t fecha \t texto              (texto libre, crudo)
  E \t order_id \t seller_id \t ... \t dias \t retraso \t tardio ...  (exportado de la bodega)
Salida (clave = order_id):
  order_id \t R \t score \t tema1,tema2,...
  order_id \t E \t tardio \t dias_retraso
"""
import sys
sys.path.insert(0, ".")
from texto_pt import normalizar, temas

for linea in sys.stdin:
    p = linea.rstrip("\n").split("\t")
    if p[0] == "R" and len(p) == 6 and p[3].isdigit():
        t = temas(normalizar(p[5])) or ["sin_tema"]
        print(f"{p[2]}\tR\t{p[3]}\t{','.join(t)}")
    elif p[0] == "E" and len(p) == 13:
        print(f"{p[1]}\tE\t{1 if p[9] == 'True' else 0}\t{p[8]}")
    else:
        print("reporter:counter:Job2,RegistrosInvalidos,1", file=sys.stderr)
