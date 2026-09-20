-- Conformed location dimension: warehouses, dark stores, supplier sites.
{{ config(materialized='table') }}

with loc as (
    select * from {{ ref('stg_location') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['location_id']) }} as location_key,
    location_id,
    location_type,
    location_name,
    city,
    state,
    case state
        when 'Maharashtra'   then 'West'
        when 'Gujarat'       then 'West'
        when 'Rajasthan'     then 'North'
        when 'Delhi'         then 'North'
        when 'Uttar Pradesh' then 'North'
        when 'Karnataka'     then 'South'
        when 'Telangana'     then 'South'
        when 'Tamil Nadu'    then 'South'
        when 'Kerala'        then 'South'
        when 'West Bengal'   then 'East'
        when 'Bihar'         then 'East'
        else 'Other'
    end                                                    as region,
    pincode
from loc
