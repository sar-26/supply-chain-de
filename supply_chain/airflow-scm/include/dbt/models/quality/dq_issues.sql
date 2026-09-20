-- Data-quality & business-rule issues, one row per detected problem, RAG-tagged.
-- Now carries location_key + city + region so issues are sliceable by geography
-- (dashboard filters, and per-region AI later). Pure SQL triage: rules set severity.
{{ config(materialized='table') }}

with soh as (
    select product_key, location_key, sum(qty_delta) as stock_on_hand
    from {{ ref('fact_inventory_movement') }}
    group by product_key, location_key
),

order_value as (
    select order_id, sum(net_sales_amt) as order_net
    from {{ ref('fact_sales') }}
    group by order_id
),

negative_stock as (
    select
        'NEGATIVE_STOCK'                                                  as check_name,
        case when stock_on_hand < -500 then 'RED' else 'AMBER' end        as severity,
        'PRODUCT_LOCATION'                                               as entity_type,
        'P' || product_key || '_L' || location_key                       as entity_ref,
        location_key                                                    as location_key,
        stock_on_hand                                                    as metric_value,
        0                                                                as threshold_value,
        'Stock on hand is negative (' || stock_on_hand ||
            '); more units sold than received'                           as detail
    from soh
    where stock_on_hand < 0
),

low_margin as (
    select
        'LOW_MARGIN'                                                     as check_name,
        case when gross_profit_amt < 0 then 'RED' else 'AMBER' end        as severity,
        'SALES_LINE'                                                     as entity_type,
        'S' || sales_key                                                 as entity_ref,
        location_key                                                    as location_key,
        round(gross_profit_amt / net_sales_amt * 100, 1)                 as metric_value,
        5                                                                as threshold_value,
        'Gross margin below 5% on this sales line'                       as detail
    from {{ ref('fact_sales') }}
    where net_sales_amt > 0
      and gross_profit_amt / net_sales_amt < 0.05
),

high_freight as (
    select
        'HIGH_FREIGHT_RATIO'                                             as check_name,
        case when s.freight_cost / o.order_net > 0.30 then 'RED'
             else 'AMBER' end                                            as severity,
        'SHIPMENT'                                                      as entity_type,
        'SH' || s.shipment_key                                          as entity_ref,
        s.location_key                                                  as location_key,
        round(s.freight_cost / o.order_net * 100, 1)                    as metric_value,
        15                                                               as threshold_value,
        'Freight cost exceeds 15% of the order value'                   as detail
    from {{ ref('fact_shipment') }} s
    join order_value o on s.order_id = o.order_id
    where o.order_net > 0
      and s.freight_cost / o.order_net > 0.15
),

sla_breach as (
    select
        'DELIVERY_SLA_BREACH'                                           as check_name,
        case when delivery_hours > 3 then 'RED' else 'AMBER' end         as severity,
        'SHIPMENT'                                                      as entity_type,
        'SH' || shipment_key                                            as entity_ref,
        location_key                                                    as location_key,
        delivery_hours                                                  as metric_value,
        2                                                                as threshold_value,
        'Delivery exceeded the 2-hour quick-commerce SLA'               as detail
    from {{ ref('fact_shipment') }}
    where delivery_hours > 2
),

all_issues as (
    select * from negative_stock
    union all select * from low_margin
    union all select * from high_freight
    union all select * from sla_breach
)

select
    {{ dbt_utils.generate_surrogate_key(['ai.check_name', 'ai.entity_ref']) }} as issue_key,
    ai.check_name,
    ai.severity,
    ai.entity_type,
    ai.entity_ref,
    ai.location_key,
    loc.city,
    nvl(loc.region, 'UNKNOWN')  as region,
    ai.metric_value,
    ai.threshold_value,
    ai.detail,
    systimestamp                as detected_at
from all_issues ai
left join {{ ref('dim_location') }} loc
       on ai.location_key = loc.location_key
