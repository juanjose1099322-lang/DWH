# Réplica del tablero en Power BI Desktop

Este kit reproduce en Power BI el tablero web del Corte 2 con las mismas cifras.
Los CSV de `powerbi/csv/` son las 7 tablas de la bodega (esquema estrella), generadas por
`python etl/exportar_powerbi.py`.

## 1. Cargar el modelo

1. **Inicio → Obtener datos → Texto/CSV**: carga los 7 archivos de `powerbi/csv/`.
   En cada uno elige *Origen del archivo: 65001 Unicode (UTF-8)* y *Delimitador: Coma*.
2. En **Transformar datos**, revisa estos tipos:
   - `dim_date[full_date]` → Fecha
   - `fact_order_items[price]`, `[freight_value]`, `[payment_value_alloc]` → Número decimal fijo
   - `fact_order_items[is_late_flag]` → Verdadero/Falso
   - Si tu Windows está en español (coma decimal), en cada columna decimal usa
     *Cambiar tipo → Usar configuración regional → Inglés (Estados Unidos)*.
3. **Vista de modelo**: crea 6 relaciones de *varios a uno*, con filtro en una sola dirección,
   desde `fact_order_items` hacia cada dimensión:

| Columna en fact_order_items | Dimensión |
|---|---|
| date_key | dim_date[date_key] |
| customer_key | dim_customer[customer_key] |
| seller_key | dim_seller[seller_key] |
| product_key | dim_product[product_key] |
| payment_type_key | dim_payment_type[payment_type_key] |
| order_status_key | dim_order_status[order_status_key] |

4. Marca `dim_date` como **tabla de fechas** (columna `full_date`).
5. Crea las jerarquías **Tiempo** (year > quarter > year_month > full_date) en `dim_date`,
   **Geografía cliente** (customer_region > customer_state > customer_city) en `dim_customer` y
   **Geografía vendedor** (seller_region > seller_state) en `dim_seller`. Con ellas el visual
   hace *drill-down* y *roll-up* igual que el ROLLUP del SQL.

## 2. Columnas calculadas

```DAX
// fact_order_items
Rango retraso =
SWITCH ( TRUE (),
    ISBLANK ( fact_order_items[delivery_delay_days] ), BLANK (),
    fact_order_items[delivery_delay_days] <= -10, "1. 10+ días antes",
    fact_order_items[delivery_delay_days] <= -1,  "2. 1-9 días antes",
    fact_order_items[delivery_delay_days] = 0,    "3. El día estimado",
    fact_order_items[delivery_delay_days] <= 3,   "4. 1-3 días tarde",
    fact_order_items[delivery_delay_days] <= 7,   "5. 4-7 días tarde",
    "6. 8+ días tarde" )

Valor pedido =
CALCULATE ( SUM ( fact_order_items[price] ) + SUM ( fact_order_items[freight_value] ),
            ALLEXCEPT ( fact_order_items, fact_order_items[order_id] ) )

Rango valor compra =
SWITCH ( TRUE (),
    fact_order_items[Valor pedido] < 50,  "1. < 50",
    fact_order_items[Valor pedido] < 100, "2. 50-100",
    fact_order_items[Valor pedido] < 200, "3. 100-200",
    fact_order_items[Valor pedido] < 500, "4. 200-500",
    "5. 500+" )
```

## 3. Medidas DAX (crear una tabla vacía `_Medidas` para agruparlas)

```DAX
Ingreso Neto =
CALCULATE ( SUM ( fact_order_items[price] ),
            dim_order_status[status_group] <> "Cancelado" )

Pedidos =
CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ),
            dim_order_status[status_group] <> "Cancelado" )

Ticket Promedio =
DIVIDE (
    CALCULATE ( SUM ( fact_order_items[price] ) + SUM ( fact_order_items[freight_value] ),
                dim_order_status[status_group] <> "Cancelado" ),
    [Pedidos] )

Flete % Producto =
DIVIDE (
    CALCULATE ( SUM ( fact_order_items[freight_value] ), dim_order_status[status_group] <> "Cancelado" ),
    [Ingreso Neto] )

% Entregas Tardías =
CALCULATE (
    AVERAGEX ( fact_order_items, IF ( fact_order_items[is_late_flag], 1, 0 ) ),
    dim_order_status[status_name] = "delivered",
    NOT ISBLANK ( fact_order_items[delivery_time_days] ) )

Días Entrega Prom =
CALCULATE ( AVERAGE ( fact_order_items[delivery_time_days] ),
            dim_order_status[status_name] = "delivered" )

Calificación Prom =
CALCULATE ( AVERAGE ( fact_order_items[review_score] ),
            dim_order_status[status_name] = "delivered",
            NOT ISBLANK ( fact_order_items[delivery_time_days] ) )

% Recompra =
VAR Clientes =
    ADDCOLUMNS ( VALUES ( dim_customer[customer_unique_id] ), "@n", [Pedidos] )
RETURN DIVIDE ( COUNTROWS ( FILTER ( Clientes, [@n] > 1 ) ), COUNTROWS ( FILTER ( Clientes, [@n] > 0 ) ) )

% Pedidos 4+ cuotas =
DIVIDE (
    CALCULATE ( [Pedidos], dim_payment_type[installments_bucket] IN { "4-6", "7+" } ),
    [Pedidos] )

// Semáforos (devuelven un color para "Formato condicional → Valor del campo")
Color Tardíos =
SWITCH ( TRUE (), [% Entregas Tardías] <= 0.05, "#1a7f45", [% Entregas Tardías] <= 0.08, "#a25d00", "#c23a3a" )

Color Flete =
SWITCH ( TRUE (), [Flete % Producto] <= 0.15, "#1a7f45", [Flete % Producto] <= 0.20, "#a25d00", "#c23a3a" )

Color Calificación =
SWITCH ( TRUE (), [Calificación Prom] >= 4.2, "#1a7f45", [Calificación Prom] >= 4.0, "#a25d00", "#c23a3a" )
```

Formato: `Ingreso Neto` y `Ticket Promedio` como moneda (R$, 0 y 2 decimales); los `%` como
porcentaje con 1 decimal; `Calificación Prom` con 2 decimales.

## 4. Diseño de la página (lienzo 16:9)

| Zona | Visual | Campos |
|---|---|---|
| Barra superior | 2 segmentaciones en botones | `dim_date[year]`, `dim_customer[customer_region]` |
| Fila de KPIs | 6 tarjetas (nuevo visual *Tarjeta*) | Ingreso Neto, Pedidos, Ticket Promedio, Flete % Producto, % Entregas Tardías, Calificación Prom (color del valor con las medidas *Color …*) |
| Fila 2, ancho completo | Gráfico de líneas | Eje: `dim_date[year_month]` · Valor: Ingreso Neto · Información sobre herramientas: Pedidos |
| Fila 3 izquierda | Columnas agrupadas | Eje: `Rango retraso` · Valor: Calificación Prom (eje Y de 1 a 5; barras rojas para los rangos "tarde" con formato condicional) |
| Fila 3 derecha | Barras horizontales | Eje: `dim_product[category_name]` · Valor: Ingreso Neto · Filtro: N superior = 10 |
| Fila 4 izquierda | Matriz | Filas: `dim_seller[seller_state]`, `dim_customer[customer_state]` · Valores: Pedidos, Días Entrega Prom, % Entregas Tardías, Calificación Prom · Filtro: Pedidos ≥ 50 · barras de datos en % tardíos |
| Fila 4 derecha | Tabla | `dim_customer[customer_state]`, Pedidos, Ticket Promedio, Flete % Producto (barras de datos) |
| Fila 5 izquierda | Columnas | Eje: `Rango valor compra` · Valor: % Pedidos 4+ cuotas |
| Fila 5 derecha | Tabla | `dim_payment_type[payment_type_es]`, Pedidos, Calificación Prom |

Agrega en cada visual un cuadro de texto pequeño con la pregunta de negocio que responde
(P1-P5 del Corte 1) y una línea de acción, igual que en el tablero web.

## 5. Valores de control (filtro: todos los años, todas las regiones)

Si tu modelo está bien armado, debes obtener:

| Medida | Valor esperado |
|---|---|
| Ingreso Neto | R$ 13.494.401 |
| Pedidos | 98.199 |
| Ticket Promedio | R$ 160,29 |
| Flete % Producto | 16,6 % |
| % Entregas Tardías | 6,6 % |
| Calificación Prom | 4,08 |
