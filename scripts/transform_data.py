import os
import sys
import psycopg2
from datetime import datetime, timedelta

def get_last_trading_date(conn, target_date):
    """
    Get the most recent available trading date before `target_date`.
    """
    cur = conn.cursor()
    query = """
    SELECT MAX(trading_date) 
    FROM daily_bars 
    WHERE trading_date < %s
    """
    cur.execute(query, (target_date,))
    result = cur.fetchone()[0]
    cur.close()
    
    return result  # Returns None if no previous trading date exists

def compute_daily_returns(target_date):
    """
    Compute daily returns using the previous available trading day's close price.
    """
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

    conn = psycopg2.connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Get the last available trading day before target_date
    previous_date = get_last_trading_date(conn, target_date)
    if not previous_date:
        print(f"No trading data available before {target_date}. Skipping update.")
        return

    print(f"Using {previous_date} as the previous trading date for {target_date}.")

    update_query = """
    WITH prev_day AS (
        SELECT ticker, close AS prev_close
        FROM daily_bars
        WHERE trading_date = %s
    )
    UPDATE daily_bars db
    SET daily_return = (db.close - pd.prev_close) / pd.prev_close
    FROM prev_day pd
    WHERE db.ticker = pd.ticker
      AND db.trading_date = %s
      AND pd.prev_close IS NOT NULL
    """
    cur.execute(update_query, (previous_date, target_date))

    print(f"Updated daily_return for {target_date}.")
    cur.close()
    conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python transform_data.py <YYYY-MM-DD>")
        sys.exit(1)

    target_date = sys.argv[1]
    compute_daily_returns(target_date)

if __name__ == "__main__":
    main()