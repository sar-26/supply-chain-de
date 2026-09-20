"""Oracle connection helper -- wallet-free one-way TLS.

Works both locally and inside the Airflow container, using host/port/service
env vars (no wallet). Requires mTLS = 'not required' on the ADB (already set).
"""
import os

import oracledb
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    host = os.environ["DB_HOST"]
    port = os.environ.get("DB_PORT", "1521")
    service = os.environ["DB_SERVICE"]
    return oracledb.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=f"tcps://{host}:{port}/{service}",
    )


if __name__ == "__main__":
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM dual")
            print("SELECT 1 ->", cur.fetchone()[0])
    print("Connection OK.")
