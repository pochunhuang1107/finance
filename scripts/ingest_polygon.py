import os
import sys
import requests
import psycopg2
from datetime import datetime

def fetch_grouped_daily(date_str, api_key):
    """
    Fetches grouped daily bars for the given date (YYYY-MM-DD).
    Returns JSON response or None if failed.
    """
    base_url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    params = {
        "adjusted": "true",
        "apiKey": api_key
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Polygon: {e}")
        return None

def insert_daily_bars(records, db_config):
    """
    Inserts a list of records into the daily_bars table.
    Each record should be a dict: {
        "ticker": str,
        "date": str (YYYY-MM-DD),
        "open": float,
        "high": float,
        "low": float,
        "close": float,
        "volume": int
    }
    """
    # Unpack db_config
    user = db_config.get("user")
    password = db_config.get("password")
    host = db_config.get("host")
    port = db_config.get("port")
    database = db_config.get("dbname")

    # Build insert query
    insert_query = """
        INSERT INTO daily_bars (ticker, trading_date, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    try:
        # Connect to Postgres
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Insert each record
        for rec in records:
            cur.execute(
                insert_query,
                (
                    rec["ticker"],
                    rec["date"],
                    rec["open"],
                    rec["high"],
                    rec["low"],
                    rec["close"],
                    rec["volume"]
                )
            )

        cur.close()
        conn.close()
        print(f"Inserted {len(records)} rows into daily_bars.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_polygon.py <YYYY-MM-DD>")
        sys.exit(1)

    date_str = sys.argv[1]

    # Get environment variables
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

    if not POSTGRES_PASSWORD:
        print("No password found: ", POSTGRES_PASSWORD)
        sys.exit(1)

    if not POLYGON_API_KEY:
        print("Error: POLYGON_API_KEY is not set in environment variables.")
        sys.exit(1)

    db_config = {
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "dbname": POSTGRES_DB,
    }

    # 1. Fetch data from Polygon
    data = fetch_grouped_daily(date_str, POLYGON_API_KEY)
    if not data or "results" not in data:
        print("No results found in Polygon response or API call failed.")
        sys.exit(1)

    # 2. Parse the results
    polygon_records = data["results"]
    records_to_insert = []
    for item in polygon_records:
        # item example: { 'T': 'AAPL', 'o': 123.45, 'h': 125.67, ... }
        ticker = item.get("T")
        open_price = item.get("o")
        high = item.get("h")
        low = item.get("l")
        close = item.get("c")
        volume = item.get("v")

        # Build dict for insertion
        record = {
            "ticker": ticker,
            "date": date_str,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        }
        records_to_insert.append(record)

    # 3. Insert into Postgres
    insert_daily_bars(records_to_insert, db_config)

if __name__ == "__main__":
    main()