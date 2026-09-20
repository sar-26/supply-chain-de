-- SCD Type 2 capture of the product catalog. dbt records a new version whenever
-- unit_price or standard_cost changes, stamping dbt_valid_from / dbt_valid_to.
-- To SEE history: change a price in the source, then re-run `dbt snapshot`.
{% snapshot product_snapshot %}
{{
    config(
      target_schema='ADMIN',
      unique_key='product_id',
      strategy='check',
      check_cols=['unit_price', 'standard_cost']
    )
}}

select
    product_id,
    sku,
    product_name,
    category,
    subcategory,
    unit_price,
    standard_cost
from {{ source('scm', 'product') }}

{% endsnapshot %}
