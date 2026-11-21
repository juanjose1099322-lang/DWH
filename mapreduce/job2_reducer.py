#!/usr/bin/env python3
"""
JOB 2 · REDUCER — completa el join: para cada pedido cruza sus reseñas con su entrega.

Un pedido puede tener varios vendedores (varias filas E): se considera tardío si
cualquiera de sus envíos llegó tarde. Los pedidos con reseña pero sin entrega registrada
(cancelados o en tránsito) quedan con estado ND.
Salida (una fila por reseña y tema):  tema \t entrega(TARDE|A_TIEMPO|ND) \t score
"""
import sys
from itertools import groupby


def registros():
    for linea in sys.stdin:
        yield linea.rstrip("\n").split("\t")


for order_id, grupo in groupby(registros(), key=lambda r: r[0]):
    resenas, tardio, hay_entrega = [], 0, False
    for r in grupo:
        if r[1] == "R":
            resenas.append((r[2], r[3].split(",")))
        else:
            hay_entrega = True
            tardio = max(tardio, int(r[2]))
    if not resenas:
        continue
    estado = ("TARDE" if tardio else "A_TIEMPO") if hay_entrega else "ND"
    print(f"reporter:counter:Job2,PedidosConResena_{estado},1", file=sys.stderr)
    for score, lista in resenas:
        for tema in lista:
            print(f"{tema}\t{estado}\t{score}")
