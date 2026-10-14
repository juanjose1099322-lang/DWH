# Crear los cubos ROLAP

Los cubos son vistas que PostgreSQL calcula con `GROUP BY CUBE`, `ROLLUP` y `GROUPING SETS`:

```
python etl/ejecutar_sql.py sql/02_cubos_rolap.sql
```{{exec}}

Lista las vistas creadas:

```
PGPASSWORD=dw_pass psql "host=localhost port=5432 dbname=olist_dw user=dw_user" -c "\dv"
```{{exec}}

Consulta el cubo geográfico (fila TOTAL = gran total del ROLLUP):

```
PGPASSWORD=dw_pass psql "host=localhost port=5432 dbname=olist_dw user=dw_user" -c "SELECT * FROM cubo_region_ticket WHERE estado_cliente = 'TOTAL' ORDER BY pedidos DESC;"
```{{exec}}

El total debe ser 98.199 pedidos con ticket promedio de R$ 160,29.
