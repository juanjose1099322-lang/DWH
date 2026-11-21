#!/usr/bin/env python3
"""
JOB 3b · MAPPER — Map-side join (caché distribuida) entregas ⋈ centroides + distancia.

centroides.tsv (salida del Job 3a, ≈19 mil filas) viaja a cada nodo con -files y se carga
en memoria; así cada mapper cruza sus entregas sin shuffle de la tabla grande.
Para cada envío calcula la distancia geodésica vendedor→cliente (fórmula de haversine) y emite
la misma métrica con tres claves: banda de distancia, ruta estado→estado y GLOBAL.
Salida : clave \t n \t km \t dias \t tardio \t score \t n_score \t km² \t dias² \t km·dias \t flete \t precio
"""
import math
import sys

centro = {}
with open("centroides.tsv", encoding="utf-8") as f:
    for linea in f:
        z, lat, lng, _ = linea.rstrip("\n").split("\t")
        centro[z] = (math.radians(float(lat)), math.radians(float(lng)))

BANDAS = [(100, "01|0-100 km"), (300, "02|100-300 km"), (700, "03|300-700 km"),
          (1200, "04|700-1.200 km"), (2000, "05|1.200-2.000 km"), (1e9, "06|Más de 2.000 km")]


def haversine(a, b):
    dlat, dlng = b[0] - a[0], b[1] - a[1]
    h = math.sin(dlat / 2) ** 2 + math.cos(a[0]) * math.cos(b[0]) * math.sin(dlng / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


for linea in sys.stdin:
    p = linea.rstrip("\n").split("\t")
    if len(p) != 13 or p[0] != "E":
        continue
    _, _, _, zs, es, zc, ec, dias, _, tardio, score, precio, flete = p
    zs, zc = zs.zfill(5), zc.zfill(5)
    if zs not in centro or zc not in centro:
        print("reporter:counter:Job3b,SinCoordenadas,1", file=sys.stderr)
        continue
    km = haversine(centro[zs], centro[zc])
    d = float(dias)
    t = 1 if tardio == "True" else 0
    s, ns = (float(score), 1) if score else (0.0, 0)
    banda = next(lbl for lim, lbl in BANDAS if km < lim)
    valores = f"1\t{km}\t{d}\t{t}\t{s}\t{ns}\t{km*km}\t{d*d}\t{km*d}\t{flete}\t{precio}"
    for clave in (f"BANDA|{banda}", f"RUTA|{es}>{ec}", "GLOBAL|todos"):
        print(f"{clave}\t{valores}")
    print("reporter:counter:Job3b,EnviosGeorreferenciados,1", file=sys.stderr)
