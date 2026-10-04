"""Lists module (Phase 5A-4) — live warehouse & dark-store master lists plus the
open/overdue purchase-order (supplier-lateness) view. Reads live from Oracle via
your existing db.py.

Run:  uvicorn lists_api:app --port 8001
Open: http://localhost:8001
"""
import os
import oracledb
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import get_connection

oracledb.defaults.fetch_lobs = False
app = FastAPI(title="Supply Chain Lists")


def _clean(v):
    """Make any value JSON-safe: decode stray bytes, pass through the rest."""
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8", "replace")
        except Exception:
            return str(v)
    return v


def q(sql, p=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, p or {})
            cols = [c[0].lower() for c in cur.description]
            return [dict(zip(cols, (_clean(x) for x in r))) for r in cur.fetchall()]


@app.get("/api/warehouses")
def warehouses():
    return q("""
        select dl.location_name,
               dl.city,
               dl.region,
               to_number(nvl(soh.on_hand,0))               as on_hand,
               to_number((select count(*) from dim_location d2
                            where d2.location_type='DARK_STORE'
                              and d2.region=dl.region))      as stores_served,
               to_number(nvl(po.open_cnt,0))               as open_pos,
               to_number(nvl(po.od_cnt,0))                 as overdue_pos
        from dim_location dl
        left join (select location_key, sum(qty_delta) as on_hand
                     from fact_inventory_movement group by location_key) soh
               on soh.location_key = dl.location_key
        left join (select to_location_id,
                          count(*) as open_cnt,
                          sum(case when expected_ts < systimestamp then 1 else 0 end) as od_cnt
                     from purchase_order where status in ('OPEN','PARTIAL')
                     group by to_location_id) po
               on po.to_location_id = dl.location_id
        where dl.location_type='WAREHOUSE'
        order by dl.region
    """)


@app.get("/api/darkstores")
def darkstores():
    return q("""
        select dl.location_name,
               dl.city,
               dl.region,
               to_number(nvl(soh.on_hand,0))        as on_hand,
               to_number(nvl(r.reorder_cnt,0))      as reorder_skus,
               to_number(nvl(r.transfer_units,0))   as transfer_units
        from dim_location dl
        left join (select location_key, sum(qty_delta) as on_hand
                     from fact_inventory_movement group by location_key) soh
               on soh.location_key = dl.location_key
        left join (select location_key,
                          count(*) as reorder_cnt,
                          sum(suggested_transfer_qty) as transfer_units
                     from recommendations where reorder_flag='Y'
                     group by location_key) r
               on r.location_key = dl.location_key
        where dl.location_type='DARK_STORE'
        order by transfer_units desc nulls last
    """)


@app.get("/api/open_pos")
def open_pos():
    return q("""
        select s.supplier_name,
               dl.location_name as warehouse,
               dl.city,
               po.status,
               to_char(po.expected_ts,'YYYY-MM-DD') as expected,
               case when po.expected_ts < systimestamp then 'OVERDUE' else 'On track' end as flag,
               to_number(nvl(it.units,0)) as units
        from purchase_order po
        join supplier s      on po.supplier_id   = s.supplier_id
        join dim_location dl on po.to_location_id = dl.location_id
        left join (select po_id, sum(quantity) as units
                     from purchase_order_item group by po_id) it on it.po_id = po.po_id
        where po.status in ('OPEN','PARTIAL')
        order by po.expected_ts
    """)


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "lists.html"), encoding="utf-8") as f:
        return f.read()
