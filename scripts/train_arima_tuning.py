import os
import sys
import csv
import numpy as np
import pandas as pd
from math import sqrt
from sqlalchemy import create_engine
from pmdarima import auto_arima

def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def main():
    # Default ticker or from command line
    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]

    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    engine = create_engine(
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    query = f"""
        SELECT trading_date, close
        FROM daily_bars
        WHERE ticker = '{ticker}'
        ORDER BY trading_date
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        sys.exit(f"No data for {ticker} in daily_bars.")

    df['trading_date'] = pd.to_datetime(df['trading_date'])
    df.set_index('trading_date', inplace=True)
    df.sort_index(inplace=True)
    df = df.asfreq('B', method='ffill')
    df.dropna(subset=['close'], inplace=True)
    if df.empty:
        sys.exit("No valid data after freq assignment.")

    # Values for train/test
    values = df['close'].values
    split_idx = int(len(values) * 0.8)
    train_vals = values[:split_idx]
    test_vals = values[split_idx:]

    # Store results in "arima_tuning_results.csv"
    csv_file = "arima_tuning_results.csv"
    header = ["ticker", "seasonal", "m", "best_order", "best_seasonal_order", "AIC", "RMSE", "MAPE"]

    # If file doesn't exist, write header
    if not os.path.isfile(csv_file):
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)

    # (seasonal=False, m=1) and (seasonal=True, m=5) to simulate weekly pattern
    seasonal_configs = [
        (False, 1),
        (True, 5),
    ]

    for seasonal, m_val in seasonal_configs:
        model = auto_arima(
            train_vals,
            start_p=0, max_p=5,
            start_q=0, max_q=5,
            d=None,
            seasonal=seasonal,
            m=m_val,
            stepwise=True,
            error_action="ignore",
            suppress_warnings=True,
            trace=True
        )

        # Forecast test set
        forecast_test = model.predict(n_periods=len(test_vals))
        forecast_test = np.array(forecast_test)
        actual_test = np.array(test_vals)

        # Compute RMSE
        rmse = sqrt(np.mean((forecast_test - actual_test) ** 2))
        mape = mean_absolute_percentage_error(actual_test, forecast_test)

        # Log to CSV
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                ticker,
                seasonal, 
                m_val,
                model.order,
                model.seasonal_order,
                model.aic(),
                f"{rmse:.4f}",
                f"{mape:.2f}"
            ])

        print(f"Done with (seasonal={seasonal}, m={m_val}): RMSE={rmse:.4f}, MAPE={mape:.2f}")

if __name__ == "__main__":
    main()