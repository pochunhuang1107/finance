# scripts/train_model.py

import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from statsmodels.tsa.arima.model import ARIMA

def main():
    # Default ticker is AAPL, or override via command-line argument
    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]

    # Read DB credentials from environment variables
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    # Create SQLAlchemy engine
    engine = create_engine(
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    # Query daily_bars for this ticker
    query = """
        SELECT trading_date, close
        FROM daily_bars
        WHERE ticker = %s
        ORDER BY trading_date
    """
    df = pd.read_sql(query, engine, params=(ticker,))

    if df.empty:
        raise ValueError(f"No data found for ticker {ticker} in daily_bars.")

    # Convert trading_date to DatetimeIndex and sort
    df['trading_date'] = pd.to_datetime(df['trading_date'])
    df.set_index('trading_date', inplace=True)
    df.sort_index(inplace=True)

    # Assign business-day frequency (B) and forward-fill any missing dates
    # so that statsmodels can forecast with a proper date index
    df = df.asfreq('B', method='ffill')

    # Drop any remaining NaNs in 'close' just in case
    df.dropna(subset=['close'], inplace=True)

    if df.empty:
        raise ValueError(f"No valid close data after frequency assignment for {ticker}.")

    # Fit a simple ARIMA(1,1,1) model
    model = ARIMA(df['close'], order=(1,1,1))
    model_fit = model.fit()

    # Print summary
    print(model_fit.summary())

    # Forecast the next business day
    forecast_steps = 1
    forecast_result = model_fit.forecast(steps=forecast_steps)
    next_day_value = forecast_result.iloc[0]
    forecast_date = forecast_result.index[0]

    print(f"\nForecasted close for next business day:")
    print(f"Date: {forecast_date}, Predicted close: {next_day_value:.2f}")

if __name__ == "__main__":
    main()
