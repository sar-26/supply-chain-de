-- Reorder points and suggested warehouse -> dark-store transfers, per product
-- per dark store.
--   reorder_point = avg daily demand x (lead_time + 3 safety days)
--   target_stock  = avg daily demand x (lead_time + 3 safety + 7 review days)
--   suggested_transfer_qty = target_stock - current stock (never negative)
-- Lead time = worst-case supplier lead time from dim_supplier (default 7 days).
{{ config(materialized='table') }}

with demand as (
    select product_key, location_key, avg_daily_demand
    from {{ ref('int_daily_demand') }}
),

soh as (
    select product_key, location_key, sum(qty_delta) as stock_on_hand
    from {{ ref('fact_inventory_movement') }}
    group by product_key, location_key
),

prod_lead as (
    select fp.product_key, max(s.lead_time_days) as lead_time_days
    from {{ ref('fact_procurement') }} fp
    join {{ ref('dim_supplier') }} s on fp.supplier_key = s.supplier_key
    group by fp.product_key
),

region_wh as (
    select region, min(location_key) as source_warehouse_key
    from {{ ref('dim_location') }}
    where location_type = 'WAREHOUSE'
    group by region
),

calc as (
    select
        d.product_key,
        d.location_key,
        d.avg_daily_demand,
        nvl(soh.stock_on_hand, 0)                                          as stock_on_hand,
        nvl(pl.lead_time_days, 7)                                          as lead_time_days,
        dp.sku,
        dp.category,
        dl.city,
        dl.region,
        rw.source_warehouse_key,
        round(d.avg_daily_demand * (nvl(pl.lead_time_days, 7) + 3), 0)     as reorder_point,
        round(d.avg_daily_demand * (nvl(pl.lead_time_days, 7) + 3 + 7), 0) as target_stock
    from demand d
    left join soh        on d.product_key = soh.product_key and d.location_key = soh.location_key
    left join prod_lead pl on d.product_key = pl.product_key
    join {{ ref('dim_product') }}  dp on d.product_key  = dp.product_key
    join {{ ref('dim_location') }} dl on d.location_key = dl.location_key
    left join region_wh rw on dl.region = rw.region
    where dl.location_type = 'DARK_STORE'
)

select
    {{ dbt_utils.generate_surrogate_key(['product_key', 'location_key']) }} as recommendation_key,
    product_key,
    sku,
    category,
    location_key,
    city,
    region,
    avg_daily_demand,
    lead_time_days,
    stock_on_hand,
    reorder_point,
    target_stock,
    case when stock_on_hand <= reorder_point then 'Y' else 'N' end          as reorder_flag,
    greatest(0, target_stock - stock_on_hand)                              as suggested_transfer_qty,
    source_warehouse_key,
    systimestamp as generated_at
from calc
