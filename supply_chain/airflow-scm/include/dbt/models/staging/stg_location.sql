-- Cleaned physical locations: warehouses, dark stores, supplier sites.
with source as (
    select * from {{ source('scm', 'location') }}
)

select
    location_id,
    upper(trim(location_type)) as location_type,
    trim(location_name)        as location_name,
    trim(city)                 as city,
    trim(state)                as state,
    trim(pincode)              as pincode,
    latitude,
    longitude,
    capacity
from source
