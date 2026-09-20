-- Grain: one shipment. delivery_hours = delivered - dispatch, in hours.
{{ config(materialized='table') }}

with sh as (
    select * from {{ ref('stg_shipment') }}
),

orders as (
    select order_id, dark_store_id from {{ ref('stg_sales_order') }}
),

locations as (
    select location_key, location_id from {{ ref('dim_location') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['sh.shipment_id']) }} as shipment_key,
    to_number(to_char(sh.dispatch_ts, 'YYYYMMDD')) as date_key,
    locations.location_key,
    sh.order_id,
    sh.carrier,
    sh.freight_cost,
    round((cast(sh.delivered_ts as date) - cast(sh.dispatch_ts as date)) * 24, 2) as delivery_hours
from sh
left join orders    on sh.order_id       = orders.order_id
left join locations on orders.dark_store_id = locations.location_id
