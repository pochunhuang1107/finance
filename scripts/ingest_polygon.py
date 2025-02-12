import os
import sys
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import time

def fetch_grouped_daily(date_str, api_key, max_retries=3):
    """
    Fetches grouped daily bars for the given date (YYYY-MM-DD).
    Returns JSON response or None if failed.
    """
    base_url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    params = {
        "adjusted": "true",
        "apiKey": api_key
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                return response.json()

            elif response.status_code == 429:  # Too Many Requests
                retry_after = int(response.headers.get("Retry-After", 60))  # Use API suggested wait time if available
                print(f"Rate limit hit. Retrying in {retry_after} seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_after)

            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Polygon: {e}")
            time.sleep(10)  # Wait 10 seconds before retrying

    print("Max retries reached. API request failed.")
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
        VALUES %s
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

        # Bulk insert
        records_list = [
            (rec["ticker"], rec["date"], rec["open"], rec["high"], rec["low"], rec["close"], rec["volume"]) 
            for rec in records
        ]
        execute_values(cur, insert_query, records_list)

        cur.close()
        conn.close()
        print(f"Inserted {len(records)} rows into daily_bars.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")

def insert_ingestion_log(date_str, row_count, duration, db_config):
    """
    Inserts an ingestion log entry into the ingestion_logs table.
    """
    log_query = """
        INSERT INTO ingestion_logs (ingestion_date, row_count, duration_seconds)
        VALUES (%s, %s, %s)
    """
    try:
        conn = psycopg2.connect(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["dbname"]
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        cur.execute(log_query, (date_str, row_count, round(duration, 2)))
        
        cur.close()
        conn.close()
        print(f"Logged ingestion: {row_count} rows on {date_str}, took {duration:.2f} seconds.")
    except psycopg2.Error as e:
        print(f"Failed to log ingestion: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_polygon.py <YYYY-MM-DD>")
        sys.exit(1)

    start_time = time.time()
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
    if not data or "resultsCount" not in data:
        print("No results found in Polygon response or API call failed.")
        sys.exit(1)
    if not data["resultsCount"]:
        print("Not a trading date")
        sys.exit(0)

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

    row_count = len(records_to_insert)
    duration = time.time() - start_time
    insert_ingestion_log(date_str, row_count, duration, db_config)

if __name__ == "__main__":
    main()