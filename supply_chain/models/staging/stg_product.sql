-- Cleaned product catalog with list price and standard cost.
with source as (
    select * from {{ source('scm', 'product') }}
)

select
    product_id,
    trim(sku)                            as sku,
    trim(product_name)                   as product_name,
    trim(category)                       as category,
    trim(subcategory)                    as subcategory,
    cast(unit_price    as number(12,2))  as unit_price,
    cast(standard_cost as number(12,2))  as standard_cost,
    created_at
from source
