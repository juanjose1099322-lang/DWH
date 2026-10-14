-- =====================================================================
-- 02_cubos_rolap.sql  ·  Capa ROLAP sobre el esquema estrella
-- Cada "cubo" es una vista relacional que agrega la tabla de hechos con
-- GROUP BY CUBE / ROLLUP / GROUPING SETS. El motor relacional (DuckDB o
-- PostgreSQL) calcula las agregaciones al vuelo: no hay almacenamiento
-- multidimensional propietario (eso sería MOLAP).
-- La función GROUPING() marca con 1 las filas de subtotal de cada nivel.
-- =====================================================================

DROP VIEW IF EXISTS cubo_ventas_categoria_estado;
DROP VIEW IF EXISTS cubo_logistica_rutas;
DROP VIEW IF EXISTS cubo_pagos_satisfaccion;
DROP VIEW IF EXISTS cubo_region_ticket;
DROP VIEW IF EXISTS vw_cubo_base;

-- ---------------------------------------------------------------------
-- 0. Vista base (capa semántica): la estrella "aplanada" con nombres de
--    negocio y medidas derivadas. Todas las vistas de cubo leen de aquí.
-- ---------------------------------------------------------------------
CREATE VIEW vw_cubo_base AS
SELECT
    f.order_id,
    f.order_item_id,
    -- Dimensión Tiempo: Año > Trimestre > Mes > Día
    d.year                         AS anio,
    d.quarter                      AS trimestre,
    d.year_month                   AS anio_mes,
    d.full_date                    AS fecha,
    d.day_of_week                  AS dia_semana,
    -- Dimensión Producto
    p.category_name                AS categoria,
    -- Dimensión Cliente: Región > Estado > Ciudad
    c.customer_region              AS region_cliente,
    c.customer_state               AS estado_cliente,
    c.customer_city                AS ciudad_cliente,
    c.customer_unique_id,
    -- Dimensión Vendedor: Región > Estado > Vendedor
    s.seller_region                AS region_vendedor,
    s.seller_state                 AS estado_vendedor,
    s.seller_id,
    -- Dimensión Pago
    pt.payment_type_es             AS tipo_pago,
    pt.installments_bucket         AS rango_cuotas,
    -- Dimensión Estado del pedido
    st.status_name                 AS estado_pedido,
    st.status_group                AS grupo_estado,
    -- Medidas base
    f.price                        AS ingreso_neto,         -- valor del producto (sin flete)
    f.freight_value                AS flete,
    f.price + f.freight_value      AS ingreso_bruto,
    f.payment_value_alloc          AS valor_pagado,
    f.review_score                 AS calificacion,
    f.delivery_time_days           AS dias_entrega,
    f.delivery_delay_days          AS dias_retraso,
    CASE WHEN f.is_late_flag THEN 1 WHEN f.is_late_flag IS NULL THEN NULL ELSE 0 END AS es_tardio,
    -- Atributo derivado a nivel de pedido: rango de valor de la compra
    CASE
        WHEN SUM(f.price + f.freight_value) OVER (PARTITION BY f.order_id) <  50 THEN '1. < 50'
        WHEN SUM(f.price + f.freight_value) OVER (PARTITION BY f.order_id) < 100 THEN '2. 50-100'
        WHEN SUM(f.price + f.freight_value) OVER (PARTITION BY f.order_id) < 200 THEN '3. 100-200'
        WHEN SUM(f.price + f.freight_value) OVER (PARTITION BY f.order_id) < 500 THEN '4. 200-500'
        ELSE '5. 500+'
    END                            AS rango_valor_compra
FROM fact_order_items f
JOIN dim_date         d  ON f.date_key         = d.date_key
JOIN dim_product      p  ON f.product_key      = p.product_key
JOIN dim_customer     c  ON f.customer_key     = c.customer_key
JOIN dim_seller       s  ON f.seller_key       = s.seller_key
JOIN dim_payment_type pt ON f.payment_type_key = pt.payment_type_key
JOIN dim_order_status st ON f.order_status_key = st.order_status_key;


-- ---------------------------------------------------------------------
-- CUBO 1 · Ventas  (pregunta de negocio 1)
--   Dimensiones: Tiempo (Año > Mes) × Producto (Categoría) × Cliente (Estado)
--   GROUP BY ROLLUP en el tiempo (jerarquía) y CUBE entre categoría y estado
--   (todas las combinaciones), excluyendo pedidos cancelados.
-- ---------------------------------------------------------------------
CREATE VIEW cubo_ventas_categoria_estado AS
SELECT
    CASE WHEN GROUPING(anio)           = 1 THEN 'TOTAL' ELSE CAST(anio AS VARCHAR(4)) END AS anio,
    CASE WHEN GROUPING(anio_mes)       = 1 THEN 'TOTAL' ELSE anio_mes       END AS anio_mes,
    CASE WHEN GROUPING(categoria)      = 1 THEN 'TOTAL' ELSE categoria      END AS categoria,
    CASE WHEN GROUPING(estado_cliente) = 1 THEN 'TOTAL' ELSE estado_cliente END AS estado_cliente,
    GROUPING(anio) + GROUPING(anio_mes) + GROUPING(categoria) + GROUPING(estado_cliente) AS nivel_agregacion,
    SUM(ingreso_neto)                                        AS ingreso_neto,
    SUM(flete)                                               AS flete,
    COUNT(DISTINCT order_id)                                 AS pedidos,
    COUNT(*)                                                 AS items,
    ROUND(CAST(SUM(ingreso_bruto) / NULLIF(COUNT(DISTINCT order_id), 0) AS NUMERIC), 2) AS ticket_promedio
FROM vw_cubo_base
WHERE grupo_estado <> 'Cancelado'
GROUP BY ROLLUP (anio, anio_mes), CUBE (categoria, estado_cliente);


-- ---------------------------------------------------------------------
-- CUBO 2 · Logística / SLA  (preguntas 2 y 5)
--   Dimensiones: Estado vendedor × Estado cliente (ruta) × Año
--   GROUPING SETS: solo las vistas que la gerencia consulta, sin el
--   costo de calcular el CUBE completo.
-- ---------------------------------------------------------------------
CREATE VIEW cubo_logistica_rutas AS
SELECT
    CASE WHEN GROUPING(estado_vendedor) = 1 THEN 'TOTAL' ELSE estado_vendedor END AS estado_vendedor,
    CASE WHEN GROUPING(estado_cliente)  = 1 THEN 'TOTAL' ELSE estado_cliente  END AS estado_cliente,
    CASE WHEN GROUPING(anio)            = 1 THEN 'TOTAL' ELSE CAST(anio AS VARCHAR(4)) END AS anio,
    COUNT(DISTINCT order_id)                                     AS pedidos_entregados,
    ROUND(CAST(AVG(dias_entrega) AS NUMERIC), 1)                 AS dias_entrega_prom,
    ROUND(CAST(AVG(dias_retraso) AS NUMERIC), 1)                 AS dias_vs_estimado_prom,
    ROUND(CAST(100.0 * AVG(es_tardio) AS NUMERIC), 1)            AS pct_tardios,
    ROUND(CAST(AVG(calificacion) AS NUMERIC), 2)                 AS calificacion_prom
FROM vw_cubo_base
WHERE estado_pedido = 'delivered' AND dias_entrega IS NOT NULL
GROUP BY GROUPING SETS (
    (estado_vendedor, estado_cliente),        -- matriz de rutas
    (estado_vendedor, estado_cliente, anio),  -- rutas por año
    (estado_vendedor),                        -- desempeño por origen
    (estado_cliente),                         -- desempeño por destino
    (anio),                                   -- tendencia anual
    ()                                        -- gran total
);


-- ---------------------------------------------------------------------
-- CUBO 3 · Pagos y satisfacción  (pregunta 4)
--   Dimensiones: Tipo de pago × Rango de cuotas × Rango de valor de compra
-- ---------------------------------------------------------------------
CREATE VIEW cubo_pagos_satisfaccion AS
SELECT
    CASE WHEN GROUPING(tipo_pago)          = 1 THEN 'TOTAL' ELSE tipo_pago          END AS tipo_pago,
    CASE WHEN GROUPING(rango_cuotas)       = 1 THEN 'TOTAL' ELSE rango_cuotas       END AS rango_cuotas,
    CASE WHEN GROUPING(rango_valor_compra) = 1 THEN 'TOTAL' ELSE rango_valor_compra END AS rango_valor_compra,
    COUNT(DISTINCT order_id)                                 AS pedidos,
    SUM(valor_pagado)                                        AS valor_pagado,
    ROUND(CAST(AVG(calificacion) AS NUMERIC), 2)             AS calificacion_prom
FROM vw_cubo_base
WHERE grupo_estado <> 'Cancelado'
GROUP BY CUBE (tipo_pago, rango_cuotas, rango_valor_compra);


-- ---------------------------------------------------------------------
-- CUBO 4 · Ticket y flete por geografía  (pregunta 3)
--   Jerarquía Cliente: Región > Estado  (ROLLUP = drill-down natural)
-- ---------------------------------------------------------------------
CREATE VIEW cubo_region_ticket AS
SELECT
    CASE WHEN GROUPING(region_cliente) = 1 THEN 'TOTAL' ELSE region_cliente END AS region_cliente,
    CASE WHEN GROUPING(estado_cliente) = 1 THEN 'TOTAL' ELSE estado_cliente END AS estado_cliente,
    COUNT(DISTINCT order_id)                                                         AS pedidos,
    ROUND(CAST(SUM(ingreso_bruto) / NULLIF(COUNT(DISTINCT order_id), 0) AS NUMERIC), 2) AS ticket_promedio,
    ROUND(CAST(100.0 * SUM(flete) / NULLIF(SUM(ingreso_neto), 0) AS NUMERIC), 1)     AS flete_pct_producto
FROM vw_cubo_base
WHERE grupo_estado <> 'Cancelado'
GROUP BY ROLLUP (region_cliente, estado_cliente);
