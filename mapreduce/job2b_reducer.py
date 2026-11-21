#!/usr/bin/env python3
"""
JOB 2b · REDUCER — agrega por tema (el mapper de este job es la identidad: cat).

Entrada : tema \t entrega \t score
Salida  : tema \t resenas \t pct_en_pedidos_tardios \t score_prom
               \t score_prom_tarde \t score_prom_a_tiempo \t pct_negativas
"""
import sys
from itertools import groupby


def registros():
    for linea in sys.stdin:
        p = linea.rstrip("\n").split("\t")
        if len(p) == 3:
            yield p[0], p[1], int(p[2])


def prom(xs):
    return f"{sum(xs) / len(xs):.2f}" if xs else ""


for tema, grupo in groupby(registros(), key=lambda r: r[0]):
    todos, tarde, a_tiempo = [], [], []
    for _, estado, s in grupo:
        todos.append(s)
        if estado == "TARDE":
            tarde.append(s)
        elif estado == "A_TIEMPO":
            a_tiempo.append(s)
    entregados = len(tarde) + len(a_tiempo)
    pct_tarde = 100 * len(tarde) / entregados if entregados else 0
    pct_neg = 100 * sum(1 for s in todos if s <= 2) / len(todos)
    print(f"{tema}\t{len(todos)}\t{pct_tarde:.1f}\t{prom(todos)}\t{prom(tarde)}\t{prom(a_tiempo)}\t{pct_neg:.1f}")
