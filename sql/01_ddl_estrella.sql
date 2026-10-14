-- =====================================================================
-- 01_ddl_estrella.sql  ·  Esquema en estrella Olist (Corte 1 → Corte 2)
-- SQL estándar: ejecuta igual en DuckDB (Colab) y PostgreSQL (Killercoda)
-- =====================================================================

-- Las vistas del cubo dependen de las tablas: se eliminan primero
DROP VIEW IF EXISTS cubo_ventas_categoria_estado;
DROP VIEW IF EXISTS cubo_logistica_rutas;
DROP VIEW IF EXISTS cubo_pagos_satisfaccion;
DROP VIEW IF EXISTS cubo_region_ticket;
DROP VIEW IF EXISTS vw_cubo_base;

DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_payment_type;
DROP TABLE IF EXISTS dim_order_status;

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,          -- AAAAMMDD
    full_date     DATE NOT NULL,
    day           SMALLINT,
    month         SMALLINT,
    month_name    VARCHAR(12),
    quarter       SMALLINT,
    year          SMALLINT,
    year_month    VARCHAR(7),                   -- nuevo en Corte 2 (nivel Mes de la jerarquía)
    day_of_week   VARCHAR(10),
    is_weekend    BOOLEAN
);

CREATE TABLE dim_customer (
    customer_key        INTEGER PRIMARY KEY,
    customer_unique_id  VARCHAR(32) NOT NULL,
    customer_city       VARCHAR(60),
    customer_state      CHAR(2),
    customer_zip_prefix INTEGER,
    customer_region     VARCHAR(15)             -- nuevo en Corte 2 (Región > Estado > Ciudad)
);

CREATE TABLE dim_seller (
    seller_key        INTEGER PRIMARY KEY,
    seller_id         VARCHAR(32) NOT NULL,
    seller_city       VARCHAR(60),
    seller_state      CHAR(2),
    seller_zip_prefix INTEGER,
    seller_region     VARCHAR(15)               -- nuevo en Corte 2
);

CREATE TABLE dim_product (
    product_key   INTEGER PRIMARY KEY,
    product_id    VARCHAR(32) NOT NULL,
    category_name VARCHAR(60),
    weight_g      DOUBLE PRECISION,
    length_cm     DOUBLE PRECISION,
    height_cm     DOUBLE PRECISION,
    width_cm      DOUBLE PRECISION,
    volume_cm3    DOUBLE PRECISION
);

CREATE TABLE dim_payment_type (
    payment_type_key    INTEGER PRIMARY KEY,
    payment_type        VARCHAR(20),
    payment_type_es     VARCHAR(25),
    installments_bucket VARCHAR(10)
);

CREATE TABLE dim_order_status (
    order_status_key INTEGER PRIMARY KEY,
    status_name      VARCHAR(20),
    status_group     VARCHAR(15)
);

CREATE TABLE fact_order_items (
    order_item_sk       INTEGER PRIMARY KEY,
    order_id            VARCHAR(32) NOT NULL,   -- dimensión degenerada
    order_item_id       SMALLINT    NOT NULL,   -- dimensión degenerada
    date_key            INTEGER REFERENCES dim_date(date_key),
    customer_key        INTEGER REFERENCES dim_customer(customer_key),
    seller_key          INTEGER REFERENCES dim_seller(seller_key),
    product_key         INTEGER REFERENCES dim_product(product_key),
    payment_type_key    INTEGER REFERENCES dim_payment_type(payment_type_key),
    order_status_key    INTEGER REFERENCES dim_order_status(order_status_key),
    price               DECIMAL(10,2),
    freight_value       DECIMAL(10,2),
    payment_value_alloc DECIMAL(10,2),
    review_score        SMALLINT,
    delivery_time_days  INTEGER,
    delivery_delay_days INTEGER,
    is_late_flag        BOOLEAN
);
