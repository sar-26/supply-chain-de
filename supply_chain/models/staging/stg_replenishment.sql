-- Warehouse to dark-store replenishment requests.
with source as (
    select * from {{ source('scm', 'replenishment') }}
)

select
    replen_id,
    product_id,
    from_location_id,
    to_location_id,
    quantity,
    upper(trim(status)) as status,
    created_ts
from source
