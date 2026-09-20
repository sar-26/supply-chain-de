-- Stock movement event log (INBOUND / SALE / TRANSFER / ADJUSTMENT).
with source as (
    select * from {{ source('scm', 'inventory_movement') }}
)

select
    movement_id,
    product_id,
    location_id,
    upper(trim(move_type)) as move_type,
    quantity,
    move_ts,
    ref_id
from source
