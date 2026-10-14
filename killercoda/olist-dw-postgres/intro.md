# Bodega de datos Olist en PostgreSQL

En este laboratorio despliegas la bodega del proyecto en una máquina Ubuntu efímera:

1. PostgreSQL 16 escuchando solo en `localhost:5432`.
2. Conexión con la **cadena estándar local** del proyecto:
   `postgresql+psycopg2://dw_user:dw_pass@localhost:5432/olist_dw`
3. Carga del esquema estrella (7 tablas, 112.650 ítems de pedido) con el ETL en Python.
4. Creación y consulta de los cubos ROLAP.

Mientras lees esto, el entorno clona el repositorio e instala PostgreSQL en segundo plano.
Espera a que exista el archivo `/root/.setup_ok`:

```
until [ -f /root/.setup_ok ]; do sleep 2; done; echo LISTO
```{{exec}}
