-- Trailing 28-day average daily demand per product per dark store.
-- This is the Phase 4 "forecast" — a moving-average baseline. It's sealed behind
-- this model, so a smarter method (Prophet) can replace it later without any
-- downstream change.
{{ config(materialized='view') }}

with sales_daily as (
    select
        f.product_key,
        f.location_key,
        dd.full_date,
        sum(f.quantity) as units_sold
    from {{ ref('fact_sales') }} f
    join {{ ref('dim_date') }} dd on f.date_key = dd.date_key
    group by f.product_key, f.location_key, dd.full_date
),

max_date as (
    select max(full_date) as md from sales_daily
),

window_sales as (
    select
        s.product_key,
        s.location_key,
        sum(s.units_sold) as units_28d
    from sales_daily s
    cross join max_date m
    where s.full_date > m.md - 28
    group by s.product_key, s.location_key
)

select
    product_key,
    location_key,
    units_28d,
    round(units_28d / 28.0, 2) as avg_daily_demand
from window_sales
