#!/usr/bin/env python
import os
import sys
import warnings
# Suppress warnings to keep the output clean
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from math import sqrt
from sqlalchemy import create_engine
from pmdarima import auto_arima
from statsmodels.tsa.arima.model import ARIMA

def mean_absolute_percentage_error(y_true, y_pred):
    """Calculate Mean Absolute Percentage Error (MAPE)."""
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def main():
    """
    This script performs the following steps:
      1. Retrieves daily 'close' price data for a given ticker from a PostgreSQL database.
      2. Processes the data (ensuring a business-day frequency).
      3. Splits the data into an 80/20 train-test set.
      4. Uses pmdarima’s auto_arima with a stepwise search to find the best ARIMA parameters (minimizing AIC).
      5. Evaluates the model using RMSE and MAPE on the test set and shows forecast vs actual prices.
      6. Re-fits the best model on the entire dataset using statsmodels’ ARIMA and forecasts one step ahead.
    """
    # Default ticker; can be overridden by a command-line argument
    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]

    # Retrieve PostgreSQL credentials from environment variables
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    # Ensure that required environment variables are set
    if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]):
        sys.exit("Error: Please set POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB environment variables.")

    # Build SQLAlchemy engine
    engine = create_engine(
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    # Query daily_bars for the 'close' price of the given ticker
    query = f"""
        SELECT trading_date, close
        FROM daily_bars
        WHERE ticker = '{ticker}'
        ORDER BY trading_date
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        sys.exit(f"Error: No data found for ticker {ticker} in daily_bars.")

    # Process the data: convert trading_date to datetime, set as index, sort, and ensure a business-day frequency
    df['trading_date'] = pd.to_datetime(df['trading_date'])
    df.set_index('trading_date', inplace=True)
    df.sort_index(inplace=True)
    df = df.asfreq('B', method='ffill')  # Fill missing business days (e.g. weekends/holidays)
    df.dropna(subset=['close'], inplace=True)
    if df.empty:
        sys.exit("Error: No valid 'close' data after frequency assignment.")

    # Train/Test Split: 80% for training and 20% for testing
    split_idx = int(len(df) * 0.8)
    train_data = df.iloc[:split_idx]['close']
    test_data = df.iloc[split_idx:]['close']

    print("Finding best ARIMA parameters using stepwise search to minimize AIC...\n")
    
    # Use auto_arima to perform a stepwise search for the best ARIMA model (no seasonality assumed)
    auto_model = auto_arima(
        train_data,
        seasonal=False,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        trace=True
    )

    # Display the best model summary
    print("\nBest model found:")
    print(auto_model.summary())

    # Forecast the test period using the best model found
    forecast_test = auto_model.predict(n_periods=len(test_data))
    forecast_test = pd.Series(forecast_test, index=test_data.index)

    # Evaluate model performance on the test set
    rmse = sqrt(np.mean((forecast_test - test_data) ** 2))
    mape = mean_absolute_percentage_error(test_data, forecast_test)

    print("\n=== Model Performance on Test Set ===")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAPE: {mape:.2f}%")
    
    # Display a table comparing forecasted values vs actual test data
    print("\n=== Forecast vs Actual (Test Set) ===")
    comparison = pd.DataFrame({"Forecast": forecast_test, "Actual": test_data})
    print(comparison.tail(10))

    # Re-fit the best model on the entire dataset using statsmodels’ ARIMA
    order = auto_model.order  # Get the best order from auto_arima
    print("\nRe-fitting best ARIMA model on the entire dataset...")
    final_model = ARIMA(df['close'], order=order)
    final_model_fit = final_model.fit()

    # Forecast one step ahead
    final_forecast = final_model_fit.forecast(steps=1)
    final_forecast_date = final_forecast.index[0]
    final_forecast_value = final_forecast.iloc[0]

    print(f"\nOne-step-ahead forecast after re-fit: {final_forecast_date}, {final_forecast_value:.2f}")

if __name__ == "__main__":
    main()