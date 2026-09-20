-- Cleaned order headers.
with source as (
    select * from {{ source('scm', 'sales_order') }}
)

select
    order_id,
    customer_id,
    dark_store_id,
    order_ts,
    upper(trim(channel)) as channel,
    upper(trim(status))  as status
from source
