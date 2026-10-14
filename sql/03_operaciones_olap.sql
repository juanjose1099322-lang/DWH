-- =====================================================================
-- 03_operaciones_olap.sql  ·  Las 5 operaciones OLAP sobre los cubos
-- Ejecutar después de 02_cubos_rolap.sql
-- =====================================================================

-- 1) ROLL-UP: de Estado a Región (subir en la jerarquía geográfica)
SELECT region_cliente, pedidos, ticket_promedio, flete_pct_producto
FROM cubo_region_ticket
WHERE estado_cliente = 'TOTAL'
ORDER BY pedidos DESC;

-- 2) DRILL-DOWN: de la Región Nordeste a sus estados (bajar un nivel)
SELECT estado_cliente, pedidos, ticket_promedio, flete_pct_producto
FROM cubo_region_ticket
WHERE region_cliente = 'Nordeste' AND estado_cliente <> 'TOTAL'
ORDER BY flete_pct_producto DESC;

-- 3) SLICE: fijar una dimensión en un valor (Año = 2018) y ver el resto
SELECT categoria, ingreso_neto, pedidos, ticket_promedio
FROM cubo_ventas_categoria_estado
WHERE anio = '2018' AND anio_mes = 'TOTAL'
  AND estado_cliente = 'TOTAL' AND categoria <> 'TOTAL'
ORDER BY ingreso_neto DESC
LIMIT 10;

-- 4) DICE: subcubo con varias dimensiones restringidas a la vez
--    (estados SP/RJ/MG × 3 categorías líderes × año 2018)
SELECT estado_cliente, categoria, ingreso_neto, pedidos
FROM cubo_ventas_categoria_estado
WHERE anio = '2018' AND anio_mes = 'TOTAL'
  AND estado_cliente IN ('SP', 'RJ', 'MG')
  AND categoria IN ('health_beauty', 'watches_gifts', 'bed_bath_table')
ORDER BY estado_cliente, ingreso_neto DESC;

-- 5) PIVOT: rotar el cubo (tipo de pago en columnas, cuotas en filas)
SELECT rango_cuotas,
       SUM(CASE WHEN tipo_pago = 'Tarjeta de crédito' THEN pedidos ELSE 0 END) AS tarjeta_credito,
       SUM(CASE WHEN tipo_pago = 'Boleto'             THEN pedidos ELSE 0 END) AS boleto,
       SUM(CASE WHEN tipo_pago = 'Vale'               THEN pedidos ELSE 0 END) AS vale,
       SUM(CASE WHEN tipo_pago = 'Tarjeta débito'     THEN pedidos ELSE 0 END) AS tarjeta_debito
FROM cubo_pagos_satisfaccion
WHERE rango_valor_compra = 'TOTAL' AND rango_cuotas <> 'TOTAL' AND tipo_pago <> 'TOTAL'
GROUP BY rango_cuotas
ORDER BY rango_cuotas;

-- =====================================================================
-- Respuesta directa a las preguntas de negocio del Corte 1
-- =====================================================================

-- P1. Evolución mensual del ingreso neto (2016-2018)
SELECT anio_mes, ingreso_neto, pedidos
FROM cubo_ventas_categoria_estado
WHERE anio_mes <> 'TOTAL' AND categoria = 'TOTAL' AND estado_cliente = 'TOTAL'
ORDER BY anio_mes;

-- P2. Vendedores (>= 30 pedidos entregados): mejor y peor cumplimiento vs. calificación
SELECT seller_id, estado_vendedor,
       COUNT(DISTINCT order_id)                          AS pedidos,
       ROUND(CAST(100.0 * AVG(es_tardio) AS NUMERIC), 1) AS pct_tardios,
       ROUND(CAST(AVG(calificacion) AS NUMERIC), 2)      AS calificacion_prom
FROM vw_cubo_base
WHERE estado_pedido = 'delivered' AND dias_entrega IS NOT NULL
GROUP BY seller_id, estado_vendedor
HAVING COUNT(DISTINCT order_id) >= 30
ORDER BY pct_tardios DESC
LIMIT 10;

-- P5. Rutas (>= 100 pedidos) con mayor porcentaje de entregas tardías
SELECT estado_vendedor || ' -> ' || estado_cliente AS ruta,
       pedidos_entregados, dias_entrega_prom, pct_tardios, calificacion_prom
FROM cubo_logistica_rutas
WHERE anio = 'TOTAL' AND estado_vendedor <> 'TOTAL' AND estado_cliente <> 'TOTAL'
  AND pedidos_entregados >= 100
ORDER BY pct_tardios DESC
LIMIT 10;
