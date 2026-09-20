-- Procurement order lines with unit cost.
with source as (
    select * from {{ source('scm', 'purchase_order_item') }}
)

select
    po_item_id,
    po_id,
    product_id,
    quantity,
    cast(unit_cost as number(12,2)) as unit_cost
from source
