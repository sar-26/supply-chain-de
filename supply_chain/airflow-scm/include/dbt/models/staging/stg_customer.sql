-- Cleaned customer records. Thin view over the raw source.
with source as (
    select * from {{ source('scm', 'customer') }}
)

select
    customer_id,
    trim(full_name)      as customer_name,
    trim(city)           as city,
    trim(state)          as state,
    trim(pincode)        as pincode,
    upper(trim(segment)) as segment,
    registered_at
from source
