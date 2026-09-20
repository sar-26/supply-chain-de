from db import get_connection

sql = """
    SELECT sku, city, region, avg_daily_demand,
           lead_time_days, stock_on_hand,
           reorder_point, suggested_transfer_qty
    FROM   recommendations
    WHERE  reorder_flag = 'Y'
    ORDER  BY suggested_transfer_qty DESC
    FETCH FIRST 15 ROWS ONLY
"""

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            print(row)