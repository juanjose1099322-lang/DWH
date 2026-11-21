# Leer resultados e integrarlos con la bodega

Temas de queja y distancia real, leídos desde HDFS:

```
hdfs dfs -cat /olist/mr/job2b_temas/part-*
hdfs dfs -cat /olist/mr/job3b_distancias/part-* | grep -v RUTA
```{{exec}}

Ingesta de las salidas en la bodega (tablas `mr_*`) y regeneración del tablero con la sección Big Data:

```
python mapreduce/cargar_resultados_dw.py
python etl/exportar_dashboard.py
```{{exec}}

Sube las evidencias al repositorio (usa un token personal de GitHub):

```
git checkout -b feature/corte3-evidencias-hadoop
git add evidencias dashboard && git commit -m "Agrega evidencias de ejecución en Hadoop (Corte 3)"
```{{exec}}
