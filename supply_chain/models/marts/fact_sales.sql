-- Grain: one order line. The margin chain lives here.
-- gross = qty * unit_price ; net = gross - discount ; cogs = qty * standard_cost
-- gross_profit = net - cogs. Tax is tracked separately (pass-through, not profit).
{{ config(materialized='table') }}

with items as (
    select * from {{ ref('stg_order_item') }}
),

orders as (
    select * from {{ ref('stg_sales_order') }}
),

products as (
    select product_key, product_id, standard_cost
    from {{ ref('dim_product') }}
    where is_current = 'Y'
),

customers as (
    select customer_key, customer_id from {{ ref('dim_customer') }}
),

locations as (
    select location_key, location_id from {{ ref('dim_location') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['items.order_item_id']) }} as sales_key,
    to_number(to_char(orders.order_ts, 'YYYYMMDD'))  as date_key,
    products.product_key,
    customers.customer_key,
    locations.location_key,
    orders.order_id,
    items.quantity,
    round(items.quantity * items.unit_price, 2)                              as gross_sales_amt,
    items.discount_amt,
    items.tax_amt,
    round(items.quantity * items.unit_price - items.discount_amt, 2)         as net_sales_amt,
    round(items.quantity * products.standard_cost, 2)                        as cogs_amt,
    round(items.quantity * items.unit_price - items.discount_amt
          - items.quantity * products.standard_cost, 2)                      as gross_profit_amt
from items
join orders     on items.order_id      = orders.order_id
join products   on items.product_id    = products.product_id
join customers  on orders.customer_id   = customers.customer_id
join locations  on orders.dark_store_id = locations.location_id
