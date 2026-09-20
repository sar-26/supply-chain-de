-- Customer dimension (touches sales only).
{{ config(materialized='table') }}

with cust as (
    select * from {{ ref('stg_customer') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_key,
    customer_id,
    city,
    state,
    segment
from cust
