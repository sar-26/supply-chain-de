-- Grain: one purchase-order line. po_amt = qty * unit_cost.
{{ config(materialized='table') }}

with poi as (
    select * from {{ ref('stg_purchase_order_item') }}
),

po as (
    select * from {{ ref('stg_purchase_order') }}
),

products as (
    select product_key, product_id from {{ ref('dim_product') }} where is_current = 'Y'
),

suppliers as (
    select supplier_key, supplier_id from {{ ref('dim_supplier') }}
),

locations as (
    select location_key, location_id from {{ ref('dim_location') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['poi.po_item_id']) }} as procurement_key,
    to_number(to_char(po.order_ts, 'YYYYMMDD')) as date_key,
    products.product_key,
    suppliers.supplier_key,
    locations.location_key,
    po.po_id,
    poi.quantity,
    poi.unit_cost,
    round(poi.quantity * poi.unit_cost, 2) as po_amt
from poi
join po        on poi.po_id          = po.po_id
join products  on poi.product_id     = products.product_id
join suppliers on po.supplier_id     = suppliers.supplier_id
join locations on po.to_location_id  = locations.location_id
