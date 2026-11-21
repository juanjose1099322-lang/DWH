# Cargar los datos en HDFS

Los insumos están en `data/hdfs_in/`: reseñas en una línea por registro, entregas exportadas desde la bodega y la geolocalización cruda.

```
hdfs dfs -mkdir -p /olist/raw /olist/mr
hdfs dfs -put -f data/hdfs_in/* /olist/raw/
hdfs dfs -ls -h /olist/raw
```{{exec}}

Cada archivo queda partido en bloques de 16 MB (configurados en `hdfs-site.xml`). Cada bloque será un *map task*:

```
hdfs fsck /olist/raw/geolocalizacion.csv -files -blocks -locations | head -20
```{{exec}}

Lectura directa desde HDFS:

```
hdfs dfs -cat /olist/raw/resenas.tsv | head -3
```{{exec}}
