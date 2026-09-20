-- Cleaned order lines with transacted price, discount and tax.
with source as (
    select * from {{ source('scm', 'order_item') }}
)

select
    order_item_id,
    order_id,
    product_id,
    quantity,
    cast(unit_price   as number(12,2)) as unit_price,
    cast(discount_amt as number(12,2)) as discount_amt,
    cast(tax_amt      as number(12,2)) as tax_amt
from source
