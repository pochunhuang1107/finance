import os
import requests
import pandas as pd

def fetch_daily_grouped_data(date: str, api_key: str):
    """
    Fetch the last trade for the given ticker from Polygon.io
    Returns JSON data with trade details.
    """
    url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date}?adjusted=true&apiKey={api_key}"
    response = requests.get(url)
    response.raise_for_status()  # Raises an HTTPError if the status is 4xx, 5xx
    return response.json()

if __name__ == "__main__":
    # Load from an environment variable or replace with your key (not recommended for production)
    POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "<YOUR_API_KEY_HERE>")

    date = "2025-01-24"
    trade_data = fetch_daily_grouped_data(date, POLYGON_API_KEY)

    results = trade_data.get("results", [])
    df = pd.DataFrame(results)
    df.rename(columns={
        "T": "ticker",
        "o": "open",
        "c": "close",
        "h": "high",
        "l": "low",
        "v": "volume",
        "vw": "vwap",
        "t": "timestamp_ms",
        "n": "trade_count"
    }, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms")

    print(df.head())