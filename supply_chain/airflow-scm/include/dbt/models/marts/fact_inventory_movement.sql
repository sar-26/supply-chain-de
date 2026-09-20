-- Grain: one stock movement event. qty_delta is signed (+ in, - out).
{{ config(materialized='table') }}

with mv as (
    select * from {{ ref('stg_inventory_movement') }}
),

products as (
    select product_key, product_id from {{ ref('dim_product') }} where is_current = 'Y'
),

locations as (
    select location_key, location_id from {{ ref('dim_location') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['mv.movement_id']) }} as movement_key,
    to_number(to_char(mv.move_ts, 'YYYYMMDD')) as date_key,
    products.product_key,
    locations.location_key,
    mv.move_type,
    mv.quantity as qty_delta
from mv
join products  on mv.product_id  = products.product_id
join locations on mv.location_id = locations.location_id
