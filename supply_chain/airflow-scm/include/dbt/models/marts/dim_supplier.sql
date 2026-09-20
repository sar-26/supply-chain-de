-- Supplier dimension (touches procurement only).
{{ config(materialized='table') }}

with sup as (
    select * from {{ ref('stg_supplier') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['supplier_id']) }} as supplier_key,
    supplier_id,
    supplier_name,
    lead_time_days
from sup
