-- Grain: one replenishment request (warehouse -> dark store).
{{ config(materialized='table') }}

with rp as (
    select * from {{ ref('stg_replenishment') }}
),

products as (
    select product_key, product_id from {{ ref('dim_product') }} where is_current = 'Y'
),

locations as (
    select location_key, location_id from {{ ref('dim_location') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['rp.replen_id']) }} as replen_key,
    to_number(to_char(rp.created_ts, 'YYYYMMDD')) as date_key,
    products.product_key,
    from_loc.location_key as from_location_key,
    to_loc.location_key   as to_location_key,
    rp.quantity,
    rp.status
from rp
join products  on rp.product_id       = products.product_id
join locations from_loc on rp.from_location_id = from_loc.location_id
join locations to_loc   on rp.to_location_id   = to_loc.location_id
