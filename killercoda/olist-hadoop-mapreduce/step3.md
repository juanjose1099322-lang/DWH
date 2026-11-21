# Ejecutar los jobs MapReduce en YARN

El script lanza los seis jobs con Hadoop Streaming, baja las salidas de HDFS y guarda todas las evidencias (logs, contadores, tiempos, métricas de YARN) en `evidencias/`:

```
bash mapreduce/run_hadoop.sh
```{{exec}}

Mientras corre, observa en la UI de YARN (puerto **8088**) cómo cada job pide un contenedor para el *ApplicationMaster* y luego contenedores para los map y reduce tasks. Desde otra terminal:

```
yarn application -list -appStates RUNNING,FINISHED
curl -s http://localhost:8088/ws/v1/cluster/metrics | python3 -m json.tool | head -25
```{{exec}}

Al final, `verificar_salidas.py` confirma que el resultado del clúster es idéntico a la ejecución de referencia.
