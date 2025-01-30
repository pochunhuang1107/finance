import os
import requests
from datetime import datetime

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def fetch_grouped_daily(date_str):
    """
    Fetches grouped daily bars for the given date (YYYY-MM-DD).
    Returns JSON response or raises an exception on failure.
    """
    base_url = "https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/"
    params = {
        "adjusted": "true",
        "apiKey": POLYGON_API_KEY
    }
    url = f"{base_url}{date_str}"
    response = requests.get(url, params=params)
    response.raise_for_status()  # Raise error if HTTP status not 200
    return response.json()

if __name__ == "__main__":
    # Example: fetch for a given date
    test_date = "2025-01-29"  # pick a known trading day
    print(f"Fetching grouped daily data for {test_date}...")
    data = fetch_grouped_daily(test_date)

    # Print out a summary
    if "results" in data:
        print(f"Number of tickers returned: {len(data['results'])}")
        # Print first ticker item as an example
        first_ticker = data['results'][0]
        print("Sample result:", first_ticker)
    else:
        print("No 'results' key found in the response. Full response:")
        print(data)