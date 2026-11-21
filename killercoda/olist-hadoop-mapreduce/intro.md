# Corte 3 · Procesamiento distribuido con Hadoop

En este laboratorio la bodega de Olist (Cortes 1 y 2) se complementa con un **clúster Hadoop pseudo-distribuido**:

- **HDFS** guarda los datos que la bodega no modela bien: 42.687 reseñas en texto libre (portugués) y 1.000.163 puntos de geolocalización.
- **YARN** asigna memoria y CPU a cada tarea.
- **MapReduce** (Hadoop Streaming con mappers y reducers en Python) hace minería de texto y cálculo de distancias reales.

Mientras lees, en segundo plano se instala Java 11 y Hadoop 3.3.6, se reconstruye la bodega y se preparan los insumos (≈4 minutos).

Espera a que aparezca `/root/.setup_ok`:

```
until [ -f /root/.setup_ok ]; do sleep 5; echo "instalando..."; done; tail -5 /root/setup.log
```{{exec}}
