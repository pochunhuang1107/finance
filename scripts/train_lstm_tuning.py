import os
import sys
import csv
import numpy as np
import pandas as pd
from math import sqrt
from sqlalchemy import create_engine

import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler

def prepare_sequences(series, lookback=30):
    X, y = [], []
    for i in range(lookback, len(series)):
        X.append(series[i - lookback:i])
        y.append(series[i])
    return np.array(X), np.array(y)

def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

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

    # Fetch data
    query = f"""
        SELECT trading_date, close
        FROM daily_bars
        WHERE ticker = '{ticker}'
        ORDER BY trading_date
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        sys.exit(f"No data for ticker {ticker}.")

    # Process datetime, freq
    df['trading_date'] = pd.to_datetime(df['trading_date'])
    df.set_index('trading_date', inplace=True)
    df.sort_index(inplace=True)
    df = df.asfreq('B', method='ffill')
    df.dropna(subset=['close'], inplace=True)
    if df.empty:
        sys.exit("No valid data after freq assignment.")

    values = df['close'].values
    # Scale
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    scaled_vals = scaler.fit_transform(values.reshape(-1,1)).flatten()

    # Train/Test
    split_idx = int(len(scaled_vals)*0.8)
    train_vals = scaled_vals[:split_idx]
    test_vals = scaled_vals[split_idx:]

    # Hyperparam combos
    lookbacks = [15, 30]
    units_list = [32, 64]
    epochs_list = [5, 10]
    batch_list = [16, 32]

    # CSV logging
    csv_file = "lstm_tuning_results.csv"
    header = ['ticker','lookback','units','epochs','batch_size','RMSE','MAPE']

    if not os.path.isfile(csv_file):
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)

    for lookback in lookbacks:
        # Prepare train/test sequences
        X_train, y_train = prepare_sequences(train_vals, lookback)
        X_test, y_test = prepare_sequences(test_vals, lookback)

        # Reshape for LSTM
        X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
        X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

        for units in units_list:
            for epochs in epochs_list:
                for batch_size in batch_list:
                    # Build model
                    model = Sequential()
                    model.add(LSTM(units, activation='tanh', input_shape=(lookback,1)))
                    model.add(Dense(1))
                    model.compile(optimizer='adam', loss='mse')

                    # Train
                    model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=0)

                    # Predict
                    pred_scaled = model.predict(X_test).flatten()

                    # Invert scaling
                    pred = scaler.inverse_transform(pred_scaled.reshape(-1,1)).flatten()
                    actual_scaled = test_vals[lookback:]
                    actual = scaler.inverse_transform(actual_scaled.reshape(-1,1)).flatten()

                    # RMSE, MAPE
                    rmse = sqrt(np.mean((pred - actual)**2))
                    mape = mean_absolute_percentage_error(actual, pred)

                    # Log
                    with open(csv_file, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([ticker, lookback, units, epochs, batch_size, f"{rmse:.4f}", f"{mape:.2f}"])

                    print(f"Tuned LSTM: lookback={lookback}, units={units}, epochs={epochs}, "
                          f"batch_size={batch_size}, RMSE={rmse:.4f}, MAPE={mape:.2f}")

if __name__ == "__main__":
    main()