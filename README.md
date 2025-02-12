# Finance ETL and Machine Learning Project

This project aims to create a **daily batch ETL pipeline** for US stock market data using the [Polygon.io](https://polygon.io/) API. The pipeline orchestrates data ingestion from Polygon into **PostgreSQL** via **Airflow**, and includes a component for **machine learning** tasks (e.g., time-series forecasting).

## Table of Contents

- [Finance ETL and Machine Learning Project](#finance-etl-and-machine-learning-project)
  - [Table of Contents](#table-of-contents)
  - [Project Overview](#project-overview)
  - [Architecture](#architecture)
  - [Directory Structure](#directory-structure)
  - [Requirements](#requirements)
  - [Setup](#setup)
    - [1. Clone the Repository](#1-clone-the-repository)
    - [2. Environment Variables (.env)](#2-environment-variables-env)
    - [3. Docker Compose](#3-docker-compose)
    - [4. Database Setup](#4-database-setup)
    - [5. Test Polygon API Script](#5-test-polygon-api-script)
  - [Usage](#usage)
    - [1. Airflow DAGs](#1-airflow-dags)
      - [Triggering DAG in Airflow](#triggering-dag-in-airflow)
        - [Email Notifications](#email-notifications)
    - [2. Scripts](#2-scripts)
      - [Local Environment Variables](#local-environment-variables)
      - [Ingestion \& Logging](#ingestion--logging)
      - [Transform Script](#transform-script)
      - [Machine Learning](#machine-learning)
    - [3. Backfill Historical Data](#3-backfill-historical-data)
      - [3.1 `backfill_polygon.sh`](#31-backfill_polygonsh)
      - [3.2 `backfill_daily_return.sh`](#32-backfill_daily_returnsh)
  - [License](#license)
  - [Contact](#contact)

---

## Project Overview

-   **Goal**: Collect daily stock market “grouped bars” from [Polygon.io](https://polygon.io/) for US stocks and store them in a Postgres database.
-   **Tooling**:
    -   **Airflow** for scheduling and orchestration
    -   **PostgreSQL** for storing historical data
    -   **Python** scripts for ingestion, transformations, and machine learning
    -   **Docker Compose** for running Airflow + Postgres locally
-   **Machine Learning**: Uses historical data (including `daily_return`) for time-series or regression models. Both **ARIMA** and **LSTM** approaches are available, with tuning scripts.

## Architecture

1. **Data Source**: Polygon.io “Grouped Daily (Bars)” endpoint.
2. **ETL**:
    - `ingest_polygon.py` to fetch a single date and insert into Postgres
    - Automatically logs ingestion stats (`row_count`, `duration_seconds`) into `ingestion_logs`
    - `transform_data.py` to calculate `daily_return`
    - **Airflow DAG** (`polygon_etl_dag.py`) orchestrating daily ingestion & transform, with email alerts on failure
3. **Database**:
    - **Postgres** holds `daily_bars` (with columns for `ticker`, `trading_date`, `open`, `close`, `daily_return`, etc.)
    - **`ingestion_logs`** table tracks ingestion job metrics
4. **ML**:
    - Multiple scripts (`train_model.py`, `train_arima_tuning.py`, `train_lstm_tuning.py`) for time-series forecasting.

## Directory Structure

```plaintext
finance/
├── dags/
│   └── polygon_etl_dag.py         # Airflow DAG for daily ingestion + transform
├── scripts/
│   ├── ingest_polygon.py          # Main ingestion script (Polygon -> Postgres), includes ingestion logging
│   ├── transform_data.py          # Computes daily_return
│   ├── train_model.py             # Basic ARIMA model example
│   ├── train_arima_tuning.py      # Auto-ARIMA hyperparameter tuning
│   ├── train_lstm_tuning.py       # LSTM hyperparameter tuning
│   └── test_polygon_api.py        # Quick script to fetch Polygon data
├── sql/
│   ├── create_tables.sql          # Includes daily_return column, unique constraints
│   └── create_logging_tables.sql  # Creates ingestion_logs table
├── docker-compose.yml             # Airflow + Postgres local setup
├── requirements.txt               # Python dependencies
├── .env                           # Environment variables (excluded from Git)
└── README.md
```

> **Note**: The `.env` file is excluded from version control. See [Environment Variables (.env)](#2-environment-variables-env) below.

## Requirements

-   **Docker Desktop** (for Docker Compose)
-   **Python 3.9+** (if you run scripts locally rather than inside Docker)
-   **Polygon.io** account & API key
-   **Git** (for version control)
-   **macOS** or **Linux** (shell scripts rely on date commands)

## Setup

### 1. Clone the Repository

```bash
cd ~/Desktop/Project
git clone https://github.com/pochunhuang1107/finance.git
cd finance
```

### 2. Environment Variables (.env)

Create a `.env` file in the **same directory** as `docker-compose.yml` (not committed to Git). For example:

```bash
# Example .env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=finance_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

YOUR_FERNET_KEY=32_char_random_string
YOUR_SECRET_KEY=some_random_string
POLYGON_API_KEY=YOUR_POLYGON_API_KEY

# For Airflow email alerts (Gmail example):
GMAIL_ACCOUNT=your_email@gmail.com
GOOGLE_APP_PASSWORD=generated_app_password
```

-   Make sure `docker-compose.yml` references these variables in **airflow-webserver** and **airflow-scheduler**.

### 3. Docker Compose

Spin up Airflow and Postgres containers:

```bash
docker compose up -d
```

-   **Airflow UI** is accessible at [http://localhost:8080](http://localhost:8080).
-   **Postgres** is at `localhost:5432` externally, `postgres:5432` internally.

### 4. Database Setup

1. **Create main table** (`daily_bars`):

    ```bash
    docker compose cp sql/create_tables.sql postgres:/tmp/create_tables.sql
    docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -f /tmp/create_tables.sql
    ```

2. **Create logging table** (`ingestion_logs`):
    ```bash
    docker compose cp sql/create_logging_tables.sql postgres:/tmp/create_logging_tables.sql
    docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -f /tmp/create_logging_tables.sql
    ```

Verify:

```bash
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\d daily_bars"
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\d ingestion_logs"
```

### 5. Test Polygon API Script

(Optional) If running scripts locally with Python:

```bash
cd ~/Desktop/Project/finance
pip install -r requirements.txt
export POLYGON_API_KEY=YOUR_POLYGON_API_KEY
python scripts/test_polygon_api.py
```

Check console output to see how many tickers were returned.

## Usage

### 1. Airflow DAGs

Your DAG **`polygon_etl_dag.py`**:

-   Runs `ingest_polygon.py` daily (fetching “yesterday’s” data).
-   Then calls `transform_data.py` to calculate `daily_return`.
-   Configured with **`email_on_failure=True`** to notify you if tasks fail.

#### Triggering DAG in Airflow

1. Go to [http://localhost:8080](http://localhost:8080).
2. Enable (unpause) `polygon_etl_dag`.
3. Check logs to confirm ingestion + transform tasks.

##### Email Notifications

-   By default, if a task fails, you’ll get an email at `GMAIL_ACCOUNT`.
-   Adjust if you have a different SMTP provider.

### 2. Scripts

#### Local Environment Variables

If you run scripts locally:

```bash
export POSTGRES_USER=admin
export POSTGRES_PASSWORD=admin
export POSTGRES_DB=finance_db
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POLYGON_API_KEY=YOUR_POLYGON_API_KEY
```

Then:

```bash
pip install -r requirements.txt
python scripts/ingest_polygon.py 2025-01-10
python scripts/transform_data.py 2025-01-10
```

#### Ingestion & Logging

-   **`ingest_polygon.py`**:
    -   Takes a date, fetches data from Polygon, inserts into `daily_bars`.
    -   Logs ingestion metrics (row_count, duration_seconds) into `ingestion_logs`.
    -   **Handles** rate limits (HTTP 429) with retry logic.

#### Transform Script

-   **`transform_data.py`**:
    -   Accepts the same date as the ingestion script.
    -   Finds the last trading date before it.
    -   Updates `daily_return = (close(t) - close(t-1)) / close(t-1)`.

#### Machine Learning

1. **`train_model.py`**:

    - Basic ARIMA(1,1,1) model on the close price.

2. **`train_arima_tuning.py`**:

    - Advanced auto-ARIMA with parameters, logs results in `arima_tuning_results.csv`.

3. **`train_lstm_tuning.py`**:
    - Grid search for LSTM hyperparams (lookback, units, etc.), logs to `lstm_tuning_results.csv`.

### 3. Backfill Historical Data

#### 3.1 `backfill_polygon.sh`

Runs `ingest_polygon.py` for each date in a range. Example:

```bash
#!/usr/bin/env bash
# backfill_polygon.sh

START_DATE="2025-01-01"
END_DATE="2025-01-31"

CURRENT_DATE="$START_DATE"

while [ "$CURRENT_DATE" != "$END_DATE" ]; do
  echo "Ingesting data for: $CURRENT_DATE"
  python scripts/ingest_polygon.py "$CURRENT_DATE"

  # Increment date by one day (macOS syntax)
  CURRENT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$CURRENT_DATE" "+%Y-%m-%d")
done

echo "Backfill complete!"
```

#### 3.2 `backfill_daily_return.sh`

Runs `transform_data.py` for each date in a range.

```bash
#!/usr/bin/env bash
# backfill_daily_return.sh

START_DATE="2025-01-01"
END_DATE="2025-01-31"

CURRENT_DATE="$START_DATE"

while [ "$CURRENT_DATE" != "$END_DATE" ]; do
  echo "Transform data for: $CURRENT_DATE"
  python scripts/transform_data.py "$CURRENT_DATE"

  # Increment date by one day
  CURRENT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$CURRENT_DATE" "+%Y-%m-%d")
done

echo "Backfill complete!"
```

## License

```text
MIT License

[Year 2025]
Permission is hereby granted, free of charge, to any person obtaining a copy...
```

## Contact

-   **Author**: Casper Huang (GitHub: [@pochunhuang1107](https://github.com/pochunhuang1107))
-   **Email**: pochun.huang1107@gmail.com

Feel free to open an issue or pull request for any questions or improvements.

---

**Happy coding and data engineering!**

-   Monitor Airflow logs via `docker compose logs -f`.
-   Check `ingestion_logs` in Postgres for row counts & durations.
-   If tasks fail, you’ll get an **email notification** (configured in `docker-compose.yml`).
