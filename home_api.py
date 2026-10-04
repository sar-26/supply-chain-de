"""Home module (Phase 5A, live) — profitability lens over the Oracle marts.
Surrogate keys (location_key/product_key) are dbt RAW hashes, so they are NEVER
converted; drilling uses the numeric business id (location_id). Money/qty columns
are BINARY_DOUBLE, so aggregates are CAST AS NUMBER before arithmetic.

Run:  uvicorn home_api:app --port 8002   |   Open: http://localhost:8002
"""
import os
import oracledb
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import get_connection

oracledb.defaults.fetch_lobs = False
app = FastAPI(title="Supply Chain Home")
HANDLING_RATE = 2

def _clean(v):
    if isinstance(v, (bytes, bytearray)):
        try: return v.decode("utf-8", "replace")
        except Exception: return str(v)
    if isinstance(v, float): return round(v, 2)
    return v

def q(sql, p=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, p or {})
            cols = [c[0].lower() for c in cur.description]
            return [dict(zip(cols, (_clean(x) for x in r))) for r in cur.fetchall()]

def status_of(m): return "Loss" if m < 0 else "Balanced" if m < 0.10 else "Profitable"
def tier(tu):     return "red" if tu > 1000 else "amber" if tu > 0 else "green"
def num(v):       return float(v or 0)
def pnl(rev, gp, logistics):
    net = gp - logistics
    return net, (net/rev if rev else 0), status_of(net/rev if rev else 0)

def load_stores():
    # location_key (surrogate RAW) used only for joins; location_id (NUMBER) is the drill id
    return q("""
        select dl.location_id store_id, dl.location_name, dl.city, dl.region,
               nvl(fs.rev,0) rev, nvl(fs.gp,0) gp, nvl(sf.frt,0) frt,
               nvl(mv.inb,0) inb, nvl(mv.outb,0) outb, nvl(rec.tu,0) transfer_units
        from dim_location dl
        left join (select location_key,
                          sum(cast(net_sales_amt as number)) rev,
                          sum(cast(gross_profit_amt as number)) gp
                     from fact_sales group by location_key) fs on fs.location_key=dl.location_key
        left join (select location_key, sum(cast(freight_cost as number)) frt
                     from fact_shipment group by location_key) sf on sf.location_key=dl.location_key
        left join (select location_key,
                          sum(case when cast(qty_delta as number)>0 then cast(qty_delta as number) else 0 end) inb,
                          sum(case when cast(qty_delta as number)<0 then -cast(qty_delta as number) else 0 end) outb
                     from fact_inventory_movement group by location_key) mv on mv.location_key=dl.location_key
        left join (select location_key, sum(cast(suggested_transfer_qty as number)) tu
                     from recommendations where reorder_flag='Y' group by location_key) rec
               on rec.location_key=dl.location_key
        where dl.location_type='DARK_STORE'
    """)

def load_wh():
    rows = q("""
        select dl.region, max(dl.location_id) wh_id, max(dl.location_name) wh_name,
               nvl(sum(abs(cast(fim.qty_delta as number))),0) units
        from dim_location dl
        left join fact_inventory_movement fim on fim.location_key = dl.location_key
        where dl.location_type='WAREHOUSE' group by dl.region
    """)
    out = {}
    for r in rows:
        r["opex"] = HANDLING_RATE * num(r.get("units"))
        out[r["region"]] = r
    return out

@app.get("/api/home/regions")
def regions():
    stores = load_stores(); wh = load_wh(); by = {}
    for s in stores:
        d = by.setdefault(s["region"] or "UNKNOWN", {"rev":0,"gp":0,"frt":0,"inb":0,"outb":0,"crit":0})
        d["rev"]+=num(s["rev"]); d["gp"]+=num(s["gp"]); d["frt"]+=num(s["frt"])
        d["inb"]+=num(s["inb"]); d["outb"]+=num(s["outb"])
        if tier(num(s["transfer_units"]))=="red": d["crit"]+=1
    rows=[]; tot={"rev":0,"gp":0,"logistics":0,"inb":0,"outb":0,"crit":0}
    for region,d in sorted(by.items()):
        opex=num(wh.get(region,{}).get("opex")); logistics=d["frt"]+opex
        net,margin,stt=pnl(d["rev"],d["gp"],logistics)
        rows.append({"name":region,"rev":round(d["rev"],2),"gp":round(d["gp"],2),"logistics":round(logistics,2),
                     "net":round(net,2),"margin":margin,"status":stt,"crit":d["crit"]})
        for k in ("rev","gp","inb","outb","crit"): tot[k]+=d[k]
        tot["logistics"]+=logistics
    net,margin,stt=pnl(tot["rev"],tot["gp"],tot["logistics"])
    tot.update({"net":round(net,2),"margin":margin,"status":stt,"name":"All India",
                "rev":round(tot["rev"],2),"gp":round(tot["gp"],2),"logistics":round(tot["logistics"],2)})
    return {"totals":tot,"rows":rows}

@app.get("/api/home/region/{region}")
def region(region: str):
    stores=[s for s in load_stores() if s["region"]==region]; wh=load_wh().get(region,{})
    opex=num(wh.get("opex"))
    srev=sum(num(s["rev"]) for s in stores); sgp=sum(num(s["gp"]) for s in stores); sfrt=sum(num(s["frt"]) for s in stores)
    inb=sum(num(s["inb"]) for s in stores); outb=sum(num(s["outb"]) for s in stores)
    crit=sum(1 for s in stores if tier(num(s["transfer_units"]))=="red")
    whlog=sfrt+opex; whnet,whm,whst=pnl(srev,sgp,whlog)
    rows=[{"name":wh.get("wh_name","Warehouse"),"rowtype":"WH","key":"",
           "rev":round(srev,2),"gp":round(sgp,2),"logistics":round(whlog,2),"net":round(whnet,2),
           "margin":whm,"status":whst,"health":crit}]
    for s in sorted(stores,key=lambda x:(num(x["gp"])-num(x["frt"]))):
        net,margin,stt=pnl(num(s["rev"]),num(s["gp"]),num(s["frt"]))
        rows.append({"name":s["location_name"],"rowtype":"DS","key":str(int(num(s["store_id"]))),
                     "rev":round(num(s["rev"]),2),"gp":round(num(s["gp"]),2),"logistics":round(num(s["frt"]),2),
                     "net":round(net,2),"margin":margin,"status":stt,"health":tier(num(s["transfer_units"]))})
    tot={"name":region,"rev":round(srev,2),"gp":round(sgp,2),"logistics":round(whlog,2),
         "net":round(whnet,2),"margin":whm,"status":whst,"inb":inb,"outb":outb}
    return {"totals":tot,"rows":rows}

def _store_meta(store_id):
    return next((s for s in load_stores() if int(num(s["store_id"]))==int(store_id)), None)

@app.get("/api/home/store/{store_id}")
def store(store_id: int):
    meta=_store_meta(store_id)
    if not meta: return {"totals":{},"rows":[]}
    cats=q("""select dp.category, sum(cast(fs.net_sales_amt as number)) rev, sum(cast(fs.gross_profit_amt as number)) gp
              from fact_sales fs
              join dim_location dl on fs.location_key=dl.location_key
              join dim_product  dp on fs.product_key=dp.product_key
              where dl.location_id=:lid group by dp.category""",{"lid":store_id})
    srev=sum(num(c["rev"]) for c in cats) or 1; sfrt=num(meta["frt"])
    rows=[]
    for c in cats:
        lo=sfrt*num(c["rev"])/srev; net,margin,stt=pnl(num(c["rev"]),num(c["gp"]),lo)
        rows.append({"name":c["category"],"rev":round(num(c["rev"]),2),"gp":round(num(c["gp"]),2),
                     "logistics":round(lo,2),"net":round(net,2),"margin":margin,"status":stt})
    rows.sort(key=lambda r:r["margin"])
    net,margin,stt=pnl(num(meta["rev"]),num(meta["gp"]),sfrt)
    tot={"name":meta["location_name"],"rev":round(num(meta["rev"]),2),"gp":round(num(meta["gp"]),2),
         "logistics":round(sfrt,2),"net":round(net,2),"margin":margin,"status":stt,"inb":meta["inb"],"outb":meta["outb"]}
    return {"totals":tot,"rows":rows}

@app.get("/api/home/category")
def category(store_id: int, category: str):
    meta=_store_meta(store_id)
    if not meta: return {"totals":{},"rows":[]}
    prods=q("""select dp.product_name, sum(cast(fs.net_sales_amt as number)) rev, sum(cast(fs.gross_profit_amt as number)) gp
               from fact_sales fs
               join dim_location dl on fs.location_key=dl.location_key
               join dim_product  dp on fs.product_key=dp.product_key
               where dl.location_id=:lid and dp.category=:cat group by dp.product_name""",
            {"lid":store_id,"cat":category})
    crev=sum(num(p["rev"]) for p in prods) or 1; srev=num(meta["rev"]) or 1
    cat_freight=num(meta["frt"])*crev/srev
    rows=[]
    for p in prods:
        lo=cat_freight*num(p["rev"])/crev; net,margin,stt=pnl(num(p["rev"]),num(p["gp"]),lo)
        rows.append({"name":p["product_name"],"rev":round(num(p["rev"]),2),"gp":round(num(p["gp"]),2),
                     "logistics":round(lo,2),"net":round(net,2),"margin":margin,"status":stt})
    rows.sort(key=lambda r:r["margin"])
    cgp=sum(num(p["gp"]) for p in prods); net,margin,stt=pnl(crev,cgp,cat_freight)
    tot={"name":category,"rev":round(crev,2),"gp":round(cgp,2),"logistics":round(cat_freight,2),
         "net":round(net,2),"margin":margin,"status":stt,"inb":meta["inb"],"outb":meta["outb"]}
    return {"totals":tot,"rows":rows}

@app.get("/api/home/trend")
def trend(region: str = "", store_id: str = "", days: int = 30):
    where="dd.full_date > (select max(full_date) from dim_date d2 join fact_sales f2 on d2.date_key=f2.date_key) - :days"
    params={"days":days}; join=""
    if store_id:
        join="join dim_location dl on fs.location_key=dl.location_key"; where+=" and dl.location_id=:lid"; params["lid"]=int(float(store_id))
    elif region:
        join="join dim_location dl on fs.location_key=dl.location_key"; where+=" and dl.region=:region"; params["region"]=region
    return q(f"""select to_char(dd.full_date,'YYYY-MM-DD') day,
                        sum(cast(fs.net_sales_amt as number)) rev, sum(cast(fs.gross_profit_amt as number)) gp
                 from fact_sales fs join dim_date dd on fs.date_key=dd.date_key {join}
                 where {where} group by dd.full_date order by dd.full_date""", params)

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__),"home.html"),encoding="utf-8") as f:
        return f.read()
