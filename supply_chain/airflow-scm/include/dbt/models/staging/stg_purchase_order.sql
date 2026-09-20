-- Procurement order headers.
with source as (
    select * from {{ source('scm', 'purchase_order') }}
)

select
    po_id,
    supplier_id,
    to_location_id,
    order_ts,
    expected_ts,
    upper(trim(status)) as status
from source
