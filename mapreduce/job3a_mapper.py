#!/usr/bin/env python3
"""
JOB 3a · MAPPER — Centroides por prefijo de código postal (1.000.163 puntos crudos).

Entrada : geolocalizacion.csv  (zip,lat,lng,ciudad,estado)  — se lee tal cual (schema-on-read)
Salida  : zip \t suma_lat \t suma_lng \t n
Regla de calidad: se descartan puntos fuera del rectángulo de Brasil (errores de captura).
"""
import sys

LAT_MIN, LAT_MAX, LNG_MIN, LNG_MAX = -34.0, 5.5, -74.0, -34.5

for linea in sys.stdin:
    p = linea.rstrip("\n").split(",")
    if len(p) < 5 or p[0].startswith('"geolocation'):
        continue
    try:
        zip_, lat, lng = p[0].strip('"'), float(p[1]), float(p[2])
    except ValueError:
        print("reporter:counter:Job3a,FilasMalformadas,1", file=sys.stderr)
        continue
    if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
        print("reporter:counter:Job3a,PuntosFueraDeBrasil,1", file=sys.stderr)
        continue
    print(f"{zip_}\t{lat}\t{lng}\t1")
