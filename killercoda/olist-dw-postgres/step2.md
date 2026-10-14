# Cargar la bodega con el ETL

El ETL descarga los 8 CSV de Olist desde el espejo público en GitHub, aplica las 8 reglas de transformación del Corte 1 y carga primero las dimensiones y después la tabla de hechos:

```
python etl/etl_olist.py
```{{exec}}

Verifica los conteos:

```
PGPASSWORD=dw_pass psql "host=localhost port=5432 dbname=olist_dw user=dw_user" -c "
SELECT 'fact_order_items' AS tabla, COUNT(*) FROM fact_order_items UNION ALL
SELECT 'dim_customer', COUNT(*) FROM dim_customer UNION ALL
SELECT 'dim_seller',   COUNT(*) FROM dim_seller   UNION ALL
SELECT 'dim_product',  COUNT(*) FROM dim_product;"
```{{exec}}

Resultado esperado: 112.650 hechos, 96.096 clientes, 3.095 vendedores y 32.951 productos.
