-- Cleaned supplier master.
with source as (
    select * from {{ source('scm', 'supplier') }}
)

select
    supplier_id,
    trim(supplier_name) as supplier_name,
    location_id,
    lead_time_days,
    created_at
from source
