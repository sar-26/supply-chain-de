"""Oracle Autonomous Database connection helper (python-oracledb, thin mode).

Thin mode needs no Oracle client install. For an Always Free Autonomous
instance we connect over mTLS using the downloaded wallet: only tnsnames.ora
and ewallet.pem are required from the wallet zip.
"""
import os

import oracledb
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Return a live connection to the Autonomous DB using .env settings."""
    return oracledb.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=os.environ["DB_DSN"],
        config_dir=os.environ["WALLET_DIR"],
        wallet_location=os.environ["WALLET_DIR"],
        wallet_password=os.environ["WALLET_PASSWORD"],
    )


if __name__ == "__main__":
    # Simple connectivity test.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM dual")
            print("SELECT 1 ->", cur.fetchone()[0])
            cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
            print("Connected to:", cur.fetchone()[0])
    print("Connection OK.")
