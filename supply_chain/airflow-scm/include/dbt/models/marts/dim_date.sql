-- Conformed calendar dimension, generated with Oracle CONNECT BY (no macro).
{{ config(materialized='table') }}

with calendar as (
    select to_date('2026-01-01','YYYY-MM-DD') + (level - 1) as full_date
    from dual
    connect by level <= (to_date('2027-01-01','YYYY-MM-DD') - to_date('2026-01-01','YYYY-MM-DD'))
)

select
    to_number(to_char(full_date, 'YYYYMMDD'))            as date_key,
    full_date,
    to_number(to_char(full_date, 'DD'))                  as day_of_month,
    to_number(to_char(full_date, 'MM'))                  as month,
    rtrim(to_char(full_date, 'Month'))                   as month_name,
    to_number(to_char(full_date, 'Q'))                   as quarter,
    to_number(to_char(full_date, 'YYYY'))                as year,
    to_number(to_char(full_date, 'IW'))                  as week_of_year,
    case when to_char(full_date, 'DY', 'NLS_DATE_LANGUAGE=ENGLISH')
              in ('SAT','SUN') then 'Y' else 'N' end     as is_weekend,
    case
        when to_number(to_char(full_date,'MM')) in (10, 11) then 'Y'
        when to_number(to_char(full_date,'MM')) = 3
             and to_number(to_char(full_date,'DD')) <= 20 then 'Y'
        when to_number(to_char(full_date,'MM')) = 1
             and to_number(to_char(full_date,'DD')) <= 15 then 'Y'
        when to_number(to_char(full_date,'MM')) = 8 then 'Y'
        else 'N'
    end                                                   as is_festival
from calendar