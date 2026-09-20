-- SCD Type 2 product dimension built on the snapshot. Surrogate key is unique
-- per version; product_id is the business key. is_current flags the live row.
{{ config(materialized='table') }}

with snap as (
    select * from {{ ref('product_snapshot') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['product_id', 'dbt_valid_from']) }} as product_key,
    product_id,
    sku,
    product_name,
    category,
    subcategory,
    unit_price,
    standard_cost,
    dbt_valid_from                                     as valid_from,
    dbt_valid_to                                       as valid_to,
    case when dbt_valid_to is null then 'Y' else 'N' end as is_current
from snap
