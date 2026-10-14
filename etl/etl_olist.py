"""
ETL Olist -> Bodega de datos en esquema estrella (Corte 2).

Implementa las 8 reglas de transformación definidas en el Corte 1 (Tabla 9)
y carga el modelo en el motor indicado por la cadena de conexión DW_URL:

    DuckDB (Google Colab / local) :  duckdb:///data/olist_dw.duckdb      (valor por defecto)
    PostgreSQL (Killercoda / local): postgresql+psycopg2://dw_user:dw_pass@localhost:5432/olist_dw

Uso:
    python etl/etl_olist.py                 # lee config/.env o variables de entorno
    DW_URL=postgresql://... python etl/etl_olist.py
"""
import os
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- #
# Configuración (standard local strings)                                       #
# --------------------------------------------------------------------------- #
def cargar_env(ruta=ROOT / "config" / ".env"):
    """Carga KEY=VALUE de config/.env sin dependencias externas."""
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

cargar_env()
DW_URL   = os.getenv("DW_URL", f"duckdb:///{ROOT / 'data' / 'olist_dw.duckdb'}")
RAW_DIR  = Path(os.getenv("RAW_DIR", ROOT / "data" / "raw"))
RAW_BASE = os.getenv(
    "RAW_BASE_URL",
    "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets",
)

# Rutas relativas de config/.env se resuelven desde la raíz del repositorio
if DW_URL.startswith("duckdb:///") and not Path(DW_URL[len("duckdb:///"):]).is_absolute():
    DW_URL = f"duckdb:///{ROOT / DW_URL[len('duckdb:///'):]}"
if not RAW_DIR.is_absolute():
    RAW_DIR = ROOT / RAW_DIR

ARCHIVOS = [
    "olist_orders_dataset.csv", "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv", "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv", "olist_sellers_dataset.csv",
    "olist_products_dataset.csv", "product_category_name_translation.csv",
]

REGION = {  # Regiones oficiales del IBGE (jerarquía Región > Estado > Ciudad)
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sur"),
}
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
PAGOS = {"credit_card": "Tarjeta de crédito", "boleto": "Boleto",
         "voucher": "Vale", "debit_card": "Tarjeta débito", "not_defined": "No definido"}
ESTADOS = {"delivered": "Completado", "shipped": "En proceso", "invoiced": "En proceso",
           "processing": "En proceso", "approved": "En proceso", "created": "En proceso",
           "canceled": "Cancelado", "unavailable": "Cancelado"}


# --------------------------------------------------------------------------- #
# EXTRACT: staging con los CSV crudos (full load)                             #
# --------------------------------------------------------------------------- #
def extraer():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for f in ARCHIVOS:
        destino = RAW_DIR / f
        if not destino.exists():
            print(f"  descargando {f} ...")
            urllib.request.urlretrieve(f"{RAW_BASE}/{f}", destino)
    lee = lambda f: pd.read_csv(RAW_DIR / f, encoding="utf-8-sig")
    return {f.replace("olist_", "").replace("_dataset.csv", "").replace(".csv", ""): lee(f)
            for f in ARCHIVOS}


# --------------------------------------------------------------------------- #
# TRANSFORM: reglas 1-8 de la Tabla 9 (Corte 1)                               #
# --------------------------------------------------------------------------- #
def transformar(s):
    log = {}
    orders, items = s["orders"].copy(), s["order_items"].copy()
    pays, revs = s["order_payments"].copy(), s["order_reviews"].copy()
    cust, sell, prod = s["customers"].copy(), s["sellers"].copy(), s["products"].copy()
    trad = s["product_category_name_translation"]

    # Regla 1: calidad de datos -------------------------------------------------
    n0 = len(items)
    items = items.drop_duplicates()
    items = items[items.order_id.isin(orders.order_id)]             # huérfanos
    items = items[(items.price > 0) & (items.freight_value >= 0)]   # valores inválidos
    log["items_descartados_r1"] = n0 - len(items)

    # Regla 2: parseo de fechas -------------------------------------------------
    for c in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
              "order_delivered_customer_date", "order_estimated_delivery_date"]:
        orders[c] = pd.to_datetime(orders[c], errors="coerce")
    revs["review_creation_date"] = pd.to_datetime(revs["review_creation_date"], errors="coerce")

    # Regla 3: traducción de categorías ----------------------------------------
    prod = prod.merge(trad, on="product_category_name", how="left")
    prod["category_name"] = prod["product_category_name_english"].fillna("sin_categoria")
    prod["volume_cm3"] = prod.product_length_cm * prod.product_height_cm * prod.product_width_cm

    # Regla 4: deduplicación de clientes por customer_unique_id ----------------
    oc = orders[["order_id", "customer_id", "order_purchase_timestamp"]].merge(cust, on="customer_id")
    ult = (oc.sort_values("order_purchase_timestamp")
             .drop_duplicates("customer_unique_id", keep="last"))      # ubicación más reciente
    dim_customer = ult[["customer_unique_id", "customer_city", "customer_state",
                        "customer_zip_code_prefix"]].reset_index(drop=True)
    dim_customer["customer_region"] = dim_customer.customer_state.map(REGION)

    # Regla 5: métricas de entrega (nulo si no hay fecha de entrega) ------------
    orders["delivery_time_days"] = (orders.order_delivered_customer_date
                                    - orders.order_purchase_timestamp).dt.days
    orders["delivery_delay_days"] = (orders.order_delivered_customer_date.dt.normalize()
                                     - orders.order_estimated_delivery_date.dt.normalize()).dt.days
    orders["is_late_flag"] = orders.delivery_delay_days.gt(0).where(orders.delivery_delay_days.notna())

    # Regla 6: alocación de pagos por ítem -------------------------------------
    pay_tot = pays.groupby("order_id", as_index=False).payment_value.sum() \
                  .rename(columns={"payment_value": "payment_total"})
    # pago principal del pedido (mayor valor) -> llave de DIM_PAYMENT_TYPE
    principal = pays.sort_values(["order_id", "payment_value"], ascending=[True, False]) \
                    .drop_duplicates("order_id")[["order_id", "payment_type", "payment_installments"]]
    items = items.merge(pay_tot, on="order_id", how="left").merge(principal, on="order_id", how="left")
    items["price_order"] = items.groupby("order_id").price.transform("sum")
    items["payment_value_alloc"] = (items.payment_total * items.price / items.price_order).round(2)

    # Regla 7: propagación de la calificación (reseña más reciente del pedido) -
    rv = revs.sort_values("review_creation_date").drop_duplicates("order_id", keep="last")
    items = items.merge(rv[["order_id", "review_score"]], on="order_id", how="left")

    # Dimensiones restantes -----------------------------------------------------
    def bucket(n):
        if pd.isna(n): return "Sin dato"
        n = int(n)
        return "1" if n <= 1 else "2-3" if n <= 3 else "4-6" if n <= 6 else "7+"
    items["payment_type"] = items.payment_type.fillna("not_defined")
    items["installments_bucket"] = items.payment_installments.map(bucket)
    dim_payment = items[["payment_type", "installments_bucket"]].drop_duplicates() \
                      .sort_values(["payment_type", "installments_bucket"]).reset_index(drop=True)
    dim_payment["payment_type_es"] = dim_payment.payment_type.map(PAGOS)

    dim_status = pd.DataFrame({"status_name": sorted(orders.order_status.unique())})
    dim_status["status_group"] = dim_status.status_name.map(ESTADOS).fillna("En proceso")

    dim_seller = sell.rename(columns={"seller_zip_code_prefix": "seller_zip_prefix"})
    dim_seller["seller_region"] = dim_seller.seller_state.map(REGION)
    dim_product = prod[["product_id", "category_name", "product_weight_g", "product_length_cm",
                        "product_height_cm", "product_width_cm", "volume_cm3"]] \
        .rename(columns={"product_weight_g": "weight_g", "product_length_cm": "length_cm",
                         "product_height_cm": "height_cm", "product_width_cm": "width_cm"})
    dim_customer = dim_customer.rename(columns={"customer_zip_code_prefix": "customer_zip_prefix"})

    fechas = pd.date_range(orders.order_purchase_timestamp.min().normalize(),
                           orders.order_purchase_timestamp.max().normalize(), freq="D")
    dim_date = pd.DataFrame({"full_date": fechas})
    dim_date["date_key"] = dim_date.full_date.dt.strftime("%Y%m%d").astype(int)
    dim_date["day"] = dim_date.full_date.dt.day
    dim_date["month"] = dim_date.full_date.dt.month
    dim_date["month_name"] = dim_date.month.map(lambda m: MESES[m - 1])
    dim_date["quarter"] = dim_date.full_date.dt.quarter
    dim_date["year"] = dim_date.full_date.dt.year
    dim_date["year_month"] = dim_date.full_date.dt.strftime("%Y-%m")
    dim_date["day_of_week"] = dim_date.full_date.dt.dayofweek.map(lambda d: DIAS[d])
    dim_date["is_weekend"] = dim_date.full_date.dt.dayofweek >= 5
    dim_date = dim_date[["date_key", "full_date", "day", "month", "month_name", "quarter",
                         "year", "year_month", "day_of_week", "is_weekend"]]

    # Regla 8: llaves subrogadas autoincrementales -----------------------------
    def sk(df, nombre):
        df = df.reset_index(drop=True)
        df.insert(0, nombre, range(1, len(df) + 1))
        return df
    dim_customer = sk(dim_customer, "customer_key")
    dim_seller   = sk(dim_seller[["seller_id", "seller_city", "seller_state",
                                  "seller_zip_prefix", "seller_region"]], "seller_key")
    dim_product  = sk(dim_product, "product_key")
    dim_payment  = sk(dim_payment[["payment_type", "payment_type_es", "installments_bucket"]],
                      "payment_type_key")
    dim_status   = sk(dim_status, "order_status_key")

    # Ensamble de la tabla de hechos (resolución de FKs) -----------------------
    f = items.merge(orders, on="order_id")
    f = f.merge(cust[["customer_id", "customer_unique_id"]], on="customer_id")
    f["date_key"] = f.order_purchase_timestamp.dt.strftime("%Y%m%d").astype(int)
    f = (f.merge(dim_customer[["customer_key", "customer_unique_id"]], on="customer_unique_id")
          .merge(dim_seller[["seller_key", "seller_id"]], on="seller_id")
          .merge(dim_product[["product_key", "product_id"]], on="product_id")
          .merge(dim_payment[["payment_type_key", "payment_type", "installments_bucket"]],
                 on=["payment_type", "installments_bucket"])
          .merge(dim_status, left_on="order_status", right_on="status_name"))
    fact = f.sort_values(["order_purchase_timestamp", "order_id", "order_item_id"])[[
        "order_id", "order_item_id", "date_key", "customer_key", "seller_key", "product_key",
        "payment_type_key", "order_status_key", "price", "freight_value", "payment_value_alloc",
        "review_score", "delivery_time_days", "delivery_delay_days", "is_late_flag"]]
    fact = sk(fact, "order_item_sk")
    for c in ["review_score", "delivery_time_days", "delivery_delay_days"]:
        fact[c] = fact[c].astype("Int64")
    fact["is_late_flag"] = fact.is_late_flag.astype("boolean")

    log["filas_fact"] = len(fact)
    return {"dim_date": dim_date, "dim_customer": dim_customer, "dim_seller": dim_seller,
            "dim_product": dim_product, "dim_payment_type": dim_payment,
            "dim_order_status": dim_status, "fact_order_items": fact}, log


# --------------------------------------------------------------------------- #
# LOAD: dimensiones primero, luego hechos                                     #
# --------------------------------------------------------------------------- #
ORDEN = ["dim_date", "dim_customer", "dim_seller", "dim_product",
         "dim_payment_type", "dim_order_status", "fact_order_items"]

def cargar(tablas):
    ddl = (ROOT / "sql" / "01_ddl_estrella.sql").read_text(encoding="utf-8")
    if DW_URL.startswith("duckdb://"):
        import duckdb
        ruta = DW_URL.replace("duckdb:///", "", 1)
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(ruta)
        con.execute(ddl)
        for t in ORDEN:
            df = tablas[t]
            con.register("tmp_df", df)
            con.execute(f"INSERT INTO {t} ({', '.join(df.columns)}) SELECT * FROM tmp_df")
            con.unregister("tmp_df")
        con.close()
    elif DW_URL.startswith("postgresql"):
        from sqlalchemy import create_engine, text
        eng = create_engine(DW_URL)
        with eng.begin() as cx:
            cx.execute(text(ddl))
        for t in ORDEN:
            tablas[t].to_sql(t, eng, if_exists="append", index=False,
                             method="multi", chunksize=5000)
    else:
        sys.exit(f"Motor no soportado en DW_URL: {DW_URL}")


if __name__ == "__main__":
    t0 = time.time()
    print(f"[1/3] Extract  -> {RAW_DIR}")
    staging = extraer()
    print("[2/3] Transform (reglas 1-8)")
    tablas, log = transformar(staging)
    for t in ORDEN:
        print(f"      {t:<18} {len(tablas[t]):>8,} filas")
    print(f"      ítems descartados por calidad: {log['items_descartados_r1']}")
    print(f"[3/3] Load     -> {DW_URL.split('@')[-1]}")
    cargar(tablas)
    print(f"ETL terminado en {time.time() - t0:.1f} s")
