"""Cockpit module (live) — the charts view: KPIs, revenue & margin trend, issue
severity, issues by region, revenue by category, delivery performance, top reorder
actions and the AI validation notes. A region filter drives most panels.

Same lessons as Home/Network: CAST money/qty AS NUMBER (they are BINARY_DOUBLE) and
never convert the RAW surrogate keys (join on them only).

Standalone:  uvicorn cockpit_api:app --port 8004   (or just run the unified app.py)
"""
import os
import oracledb
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import get_connection

oracledb.defaults.fetch_lobs = False      # AI-note CLOBs come back as plain strings
app = FastAPI(title="Supply Chain Cockpit")

SLA_HOURS = 2     # delivery SLA used for the breach % (matches the dq_issues rule)


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

def num(v): return float(v or 0)
def first(rows): return rows[0] if rows else {}


@app.get("/api/cockpit/kpis")
def kpis(region: str = "ALL"):
    reg = region != "ALL"; p = {"region": region} if reg else {}
    s = first(q("select sum(cast(fs.net_sales_amt as number)) rev, "
                "       sum(cast(fs.gross_profit_amt as number)) gp from fact_sales fs "
                + ("join dim_location dl on fs.location_key=dl.location_key where dl.region=:region" if reg else ""), p))
    d = first(q("select count(*) total, sum(case when severity='RED' then 1 else 0 end) red from dq_issues"
                + (" where region=:region" if reg else ""), p))
    r = first(q("select count(*) c from recommendations where reorder_flag='Y'"
                + (" and region=:region" if reg else ""), p))
    rev, gp = num(s.get("rev")), num(s.get("gp"))
    return {"revenue": round(rev), "gross_profit": round(gp), "margin": (gp / rev if rev else 0),
            "open_issues": int(num(d.get("total"))), "red_issues": int(num(d.get("red"))),
            "reorder_count": int(num(r.get("c")))}


@app.get("/api/cockpit/revenue_trend")
def revenue_trend(region: str = "ALL", days: int = 30):
    reg = region != "ALL"; p = {"days": days}
    if reg: p["region"] = region
    return q("select to_char(dd.full_date,'YYYY-MM-DD') day, "
             "       sum(cast(fs.net_sales_amt as number)) rev, sum(cast(fs.gross_profit_amt as number)) gp "
             "from fact_sales fs join dim_date dd on fs.date_key=dd.date_key "
             + ("join dim_location dl on fs.location_key=dl.location_key " if reg else "")
             + "where dd.full_date > (select max(d2.full_date) from dim_date d2 "
               "                      join fact_sales f2 on d2.date_key=f2.date_key) - :days "
             + ("and dl.region=:region " if reg else "")
             + "group by dd.full_date order by dd.full_date", p)


@app.get("/api/cockpit/issues_by_severity")
def issues_by_severity(region: str = "ALL"):
    reg = region != "ALL"
    return q("select severity, count(*) cnt from dq_issues "
             + ("where region=:region " if reg else "") + "group by severity order by severity",
             {"region": region} if reg else {})


@app.get("/api/cockpit/issues_by_region")
def issues_by_region():
    return q("select nvl(region,'UNKNOWN') region, severity, count(*) cnt from dq_issues "
             "group by nvl(region,'UNKNOWN'), severity order by 1")


@app.get("/api/cockpit/revenue_by_category")
def revenue_by_category(region: str = "ALL"):
    reg = region != "ALL"
    return q("select dp.category, sum(cast(fs.net_sales_amt as number)) rev, "
             "       sum(cast(fs.gross_profit_amt as number)) gp "
             "from fact_sales fs join dim_product dp on fs.product_key=dp.product_key "
             + ("join dim_location dl on fs.location_key=dl.location_key where dl.region=:region " if reg else "")
             + "group by dp.category order by rev desc", {"region": region} if reg else {})


@app.get("/api/cockpit/delivery")
def delivery(region: str = "ALL"):
    reg = region != "ALL"; p = {"sla": SLA_HOURS}
    if reg: p["region"] = region
    return q("select s.carrier, round(avg(cast(s.delivery_hours as number)),2) avg_hours, "
             "       count(*) shipments, "
             "       round(sum(case when cast(s.delivery_hours as number) > :sla then 1 else 0 end)/count(*)*100,1) sla_breach_pct "
             "from fact_shipment s "
             + ("join dim_location dl on s.location_key=dl.location_key " if reg else "")
             + "where s.delivery_hours is not null "
             + ("and dl.region=:region " if reg else "")
             + "group by s.carrier order by shipments desc", p)


@app.get("/api/cockpit/top_recommendations")
def top_recommendations(region: str = "ALL"):
    reg = region != "ALL"
    return q("select sku, city, region, cast(reorder_point as number) reorder_point, "
             "       cast(stock_on_hand as number) stock_on_hand, "
             "       cast(suggested_transfer_qty as number) transfer_qty "
             "from recommendations where reorder_flag='Y' "
             + ("and region=:region " if reg else "")
             + "order by 6 desc fetch first 10 rows only", {"region": region} if reg else {})


@app.get("/api/cockpit/ai_notes")
def ai_notes():
    return q("select check_name, severity, issue_count, explanation, recommendation "
             "from issue_explanations order by decode(severity,'RED',1,'AMBER',2,3), check_name")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cockpit.html"), encoding="utf-8") as f:
        return f.read()
