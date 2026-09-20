-- Order shipment legs with freight cost.
with source as (
    select * from {{ source('scm', 'shipment') }}
)

select
    shipment_id,
    order_id,
    trim(carrier)                      as carrier,
    cast(freight_cost as number(12,2)) as freight_cost,
    dispatch_ts,
    delivered_ts,
    upper(trim(status))                as status
from source
