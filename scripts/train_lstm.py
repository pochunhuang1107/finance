#!/usr/bin/env python
import os
import sys
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
from sklearn.preprocessing import MinMaxScaler
from math import sqrt

def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def prepare_sequences(series, lookback=30):
    """
    Convert a 1D array (series) into supervised learning samples
    of shape (num_samples, lookback_steps).
    E.g., for a lookback of 30 days, X_t is the 30 days before day t.
    """
    X, y = [], []
    for i in range(lookback, len(series)):
        X.append(series[i-lookback:i])
        y.append(series[i])
    return np.array(X), np.array(y)

def main():
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

    # Query daily_bars
    query = f"""
        SELECT trading_date, close
        FROM daily_bars
        WHERE ticker = '{ticker}'
        ORDER BY trading_date
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        sys.exit(f"No data for {ticker}.")

    # Convert to datetime, freq='B', forward-fill
    df['trading_date'] = pd.to_datetime(df['trading_date'])
    df.set_index('trading_date', inplace=True)
    df.sort_index(inplace=True)
    df = df.asfreq('B', method='ffill')
    df.dropna(subset=['close'], inplace=True)

    if df.empty:
        sys.exit("No valid data after freq assignment.")

    # Convert close to a NumPy array
    values = df['close'].values

    # Normalize data (optional): scale between 0 and 1
    scaler = MinMaxScaler()
    values_scaled = scaler.fit_transform(values.reshape(-1,1)).flatten()

    # Train/Test split
    split_idx = int(len(values_scaled) * 0.8)
    train_vals = values_scaled[:split_idx]
    test_vals = values_scaled[split_idx:]

    lookback = 30
    X_train, y_train = prepare_sequences(train_vals, lookback=lookback)
    X_test, y_test = prepare_sequences(test_vals, lookback=lookback)

    # Reshape for LSTM: (samples, timesteps, features=1)
    X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
    X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))

    # Build simple LSTM model
    model = Sequential([
        Input(shape=(30, 1)),  # Use this instead of passing input_shape in LSTM
        LSTM(50),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')

    # Train
    model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=1)

    # Predict on test
    y_pred_scaled = model.predict(X_test).flatten()

    # Invert scaling
    y_pred = scaler.inverse_transform(y_pred_scaled.reshape(-1,1)).flatten()
    y_true = test_vals[lookback:]  # these are scaled, so invert:
    y_true_inverted = scaler.inverse_transform(y_true.reshape(-1,1)).flatten()

    # Evaluate
    rmse = sqrt(np.mean((y_pred - y_true_inverted)**2))
    mape = mean_absolute_percentage_error(y_true_inverted, y_pred)

    print(f"\n=== LSTM Model Evaluation: {ticker} ===")
    print(f"Lookback: {lookback} days, Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAPE: {mape:.2f}%")

if __name__ == "__main__":
    main()