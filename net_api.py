"""Network module (Phase 5A, live) — control-tower data over the Oracle marts.
Node health, store/warehouse detail, open POs. Sourcing distance + transfer cost +
price simulator are computed in the frontend (geometry + business constants).
Lessons applied: drill by numeric location_id; CAST money/qty AS NUMBER; never
convert the RAW surrogate keys (join on them only).

Run:  uvicorn net_api:app --port 8003   |   Open: http://localhost:8003
"""
import os
import oracledb
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import get_connection

oracledb.defaults.fetch_lobs = False
app = FastAPI(title="Supply Chain Network")

def _clean(v):
    if isinstance(v,(bytes,bytearray)):
        try: return v.decode("utf-8","replace")
        except Exception: return str(v)
    if isinstance(v,float): return round(v,2)
    return v
def q(sql,p=None):
    with get_connection() as c:
        with c.cursor() as cur:
            cur.execute(sql,p or {})
            cols=[d[0].lower() for d in cur.description]
            return [dict(zip(cols,(_clean(x) for x in r))) for r in cur.fetchall()]
def num(v): return float(v or 0)
def tier(tu): return "red" if tu>1000 else "amber" if tu>0 else "green"

@app.get("/api/net/nodes")
def nodes():
    rows=q("""
        select dl.location_id, dl.location_name, dl.city, dl.region, dl.location_type,
               nvl(soh.on_hand,0) on_hand, nvl(rec.tu,0) shortfall,
               nvl(mv.inb,0) inb, nvl(mv.outb,0) outb
        from dim_location dl
        left join (select location_key, sum(cast(qty_delta as number)) on_hand
                     from fact_inventory_movement group by location_key) soh on soh.location_key=dl.location_key
        left join (select location_key, sum(cast(suggested_transfer_qty as number)) tu
                     from recommendations where reorder_flag='Y' group by location_key) rec on rec.location_key=dl.location_key
        left join (select location_key,
                          sum(case when cast(qty_delta as number)>0 then cast(qty_delta as number) else 0 end) inb,
                          sum(case when cast(qty_delta as number)<0 then -cast(qty_delta as number) else 0 end) outb
                     from fact_inventory_movement group by location_key) mv on mv.location_key=dl.location_key
        where dl.location_type in ('WAREHOUSE','DARK_STORE')
    """)
    out=[]
    for r in rows:
        wh=r["location_type"]=="WAREHOUSE"
        sev = ("amber" if num(r["on_hand"])<2000 else "green") if wh else tier(num(r["shortfall"]))
        out.append({"id":int(num(r["location_id"])),"name":r["location_name"],"city":r["city"],
                    "region":r["region"],"type":"WH" if wh else "DS","sev":sev,
                    "surplus":round(num(r["on_hand"]),0),"shortfall":round(num(r["shortfall"]),0),
                    "inb":round(num(r["inb"]),0),"outb":round(num(r["outb"]),0)})
    return out

@app.get("/api/net/store/{store_id}")
def store(store_id:int):
    cats=q("""select r.category, sum(cast(r.avg_daily_demand as number)) dpd
              from recommendations r join dim_location dl on r.location_key=dl.location_key
              where dl.location_id=:lid group by r.category order by dpd desc""",{"lid":store_id})
    prods=q("""select r.sku, r.category, cast(r.avg_daily_demand as number) dpd,
                      cast(r.stock_on_hand as number) oh, cast(r.suggested_transfer_qty as number) move
               from recommendations r join dim_location dl on r.location_key=dl.location_key
               where dl.location_id=:lid and r.reorder_flag='Y' order by move desc""",{"lid":store_id})
    pc=q("""select sum(cast(fs.net_sales_amt as number)) rev, sum(cast(fs.cogs_amt as number)) cogs,
                   sum(cast(fs.quantity as number)) qty
            from fact_sales fs join dim_location dl on fs.location_key=dl.location_key
            where dl.location_id=:lid""",{"lid":store_id})
    rev=num(pc[0]["rev"]); cogs=num(pc[0]["cogs"]); qty=num(pc[0]["qty"]) or 1
    short=sum(num(p["move"]) for p in prods)
    return {"cats":[{"cat":c["category"],"dpd":round(num(c["dpd"]),1)} for c in cats],
            "prods":[{"sku":p["sku"],"cat":p["category"],"dpd":round(num(p["dpd"]),1),
                      "oh":round(num(p["oh"]),0),"move":round(num(p["move"]),0)} for p in prods],
            "shortfall":round(short,0),"avg_price":round(rev/qty,2),"avg_cost":round(cogs/qty,2)}

@app.get("/api/net/warehouse/{wh_id}")
def warehouse(wh_id:int):
    meta=q("""select dl.region, nvl(soh.on_hand,0) surplus, nvl(mv.inb,0) inb, nvl(mv.outb,0) outb,
                     (select count(*) from dim_location d2 where d2.location_type='DARK_STORE' and d2.region=dl.region) served
              from dim_location dl
              left join (select location_key, sum(cast(qty_delta as number)) on_hand from fact_inventory_movement group by location_key) soh on soh.location_key=dl.location_key
              left join (select location_key,
                                sum(case when cast(qty_delta as number)>0 then cast(qty_delta as number) else 0 end) inb,
                                sum(case when cast(qty_delta as number)<0 then -cast(qty_delta as number) else 0 end) outb
                           from fact_inventory_movement group by location_key) mv on mv.location_key=dl.location_key
              where dl.location_id=:lid""",{"lid":wh_id})
    m=meta[0] if meta else {"surplus":0,"inb":0,"outb":0,"served":0}
    pos=q("""select s.supplier_name sup, to_char(po.expected_ts,'YYYY-MM-DD') expected,
                    case when po.expected_ts<systimestamp then 1 else 0 end overdue,
                    nvl(it.units,0) units
             from purchase_order po join supplier s on po.supplier_id=s.supplier_id
             join dim_location dl on po.to_location_id=dl.location_id
             left join (select po_id, sum(cast(quantity as number)) units from purchase_order_item group by po_id) it on it.po_id=po.po_id
             where dl.location_id=:lid and po.status in ('OPEN','PARTIAL') order by po.expected_ts""",{"lid":wh_id})
    surplus=num(m["surplus"]); outb=num(m["outb"])
    cover=round(surplus/max(1.0,outb/90.0)) if surplus>0 else 0
    return {"surplus":round(surplus,0),"inb":round(num(m["inb"]),0),"outb":round(outb,0),
            "served":int(num(m["served"])),"cover":cover,
            "pos":[{"sup":p["sup"],"expected":p["expected"],"overdue":int(num(p["overdue"])),
                    "units":round(num(p["units"]),0)} for p in pos]}

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__),"network.html"),encoding="utf-8") as f:
        return f.read()
