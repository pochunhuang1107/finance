# Finance ETL and Machine Learning Project

This project aims to create a **daily batch ETL pipeline** for US stock market data using the [Polygon.io](https://polygon.io/) API. The pipeline orchestrates data ingestion from Polygon into **PostgreSQL** via **Airflow**, and includes a component for **machine learning** tasks (e.g., time-series forecasting).

## Table of Contents

-   [Finance ETL and Machine Learning Project](#finance-etl-and-machine-learning-project)
    -   [Table of Contents](#table-of-contents)
    -   [Project Overview](#project-overview)
    -   [Architecture](#architecture)
    -   [Directory Structure](#directory-structure)
        -   [2. Environment Variables (.env)](#2-environment-variables-env)
        -   [3. Docker Compose](#3-docker-compose)
        -   [4. Database Setup](#4-database-setup)
        -   [5. Test Polygon API Script](#5-test-polygon-api-script)
    -   [Usage](#usage)
        -   [1. Airflow DAGs](#1-airflow-dags)
            -   [Triggering DAG in Airflow](#triggering-dag-in-airflow)
        -   [2. Ingestion \& Transform Scripts](#2-ingestion--transform-scripts)
        -   [3. Backfill Historical Data](#3-backfill-historical-data)
            -   [3.1 `backfill_polygon.sh`](#31-backfill_polygonsh)
            -   [3.2 `backfill_daily_return.sh`](#32-backfill_daily_returnsh)
        -   [4. Model Training (Future)](#4-model-training-future)
    -   [License](#license)
    -   [Contact](#contact)

---

## Project Overview

-   **Goal**: Collect daily stock market “grouped bars” from [Polygon.io](https://polygon.io/) for US stocks and store them in a Postgres database.
-   **Tooling**:
    -   **Airflow** for scheduling and orchestration
    -   **PostgreSQL** for storing historical data
    -   **Python** scripts for ingestion and transformations
    -   **Docker Compose** for running Airflow + Postgres locally
-   **Machine Learning**: Uses historical data (including `daily_return`) for time-series or regression models.

## Architecture

1. **Data Source**: Polygon.io “Grouped Daily (Bars)” endpoint.
2. **ETL**:
    - `ingest_polygon.py` to fetch a single date and insert into Postgres
    - `transform_data.py` to calculate `daily_return`
    - **Airflow DAG** (`polygon_etl_dag.py`) orchestrating daily ingestion & transform
3. **Database**:
    - **Postgres** holds all data in `daily_bars` (with columns for `ticker`, `trading_date`, `open`, `close`, `daily_return`, etc.)
4. **ML**: (Future) A script or DAG to train predictive models on the stored data.

## Directory Structure

````plaintext
finance/
├── dags/
│   └── polygon_etl_dag.py        # Airflow DAG for daily ingestion + transform
├── scripts/
│   ├── ingest_polygon.py         # Main ingestion script
│   ├── transform_data.py         # Computes daily_return
│   └── test_polygon_api.py       # Quick script to fetch Polygon data
├── sql/
│   └── create_tables.sql         # Includes daily_return column
├── docker-compose.yml            # Airflow + Postgres local setup
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (excluded from Git)
└── README.md

> **Note**: The `.env` file is excluded from version control. See [Environment Variables (.env)](#2-environment-variables-env) below.

## Requirements

- **Docker Desktop** (for Docker Compose)
- **Python 3.9+** (if you run scripts locally instead of inside Docker)
- **Polygon.io** account & API key
- **Git** (for version control)
- **macOS** or **Linux** (your shell scripts use date increment commands)

## Setup

### 1. Clone the Repository

```bash
cd ~/Desktop/Project
git clone https://github.com/pochunhuang1107/finance.git
cd finance
````

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
```

-   Ensure `docker-compose.yml` references these variables for **airflow-webserver** and **airflow-scheduler**.

### 3. Docker Compose

Spin up Airflow and Postgres containers:

```bash
docker compose up -d
```

-   **Airflow UI** is accessible at [http://localhost:8080](http://localhost:8080)
-   **Postgres** is at `localhost:5432` externally, and `postgres:5432` internally in Docker.

### 4. Database Setup

Initialize `daily_bars` (which already includes `daily_return`):

```bash
docker compose cp sql/create_tables.sql postgres:/tmp/create_tables.sql
docker compose exec postgres psql \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -f /tmp/create_tables.sql
```

Verify:

```bash
docker compose exec postgres psql \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -c "\d daily_bars"
```

### 5. Test Polygon API Script

If you want to run a quick test locally (with Python and `requests` installed):

```bash
cd ~/Desktop/Project/finance
pip install -r requirements.txt
export POLYGON_API_KEY=YOUR_POLYGON_API_KEY
python scripts/test_polygon_api.py
```

Ensure it prints out the number of tickers returned for the chosen date.

## Usage

### 1. Airflow DAGs

Your main DAG is `polygon_etl_dag.py`, which:

1. **Ingests** daily data for yesterday (`ingest_polygon.py`)
2. **Transforms** it by computing `daily_return` (`transform_data.py`)

#### Triggering DAG in Airflow

1. Go to [http://localhost:8080](http://localhost:8080)
2. Enable (“unpause”) `polygon_etl_dag`
3. View logs to confirm ingestion + transformation

### 2. Ingestion & Transform Scripts

-   **`ingest_polygon.py`**:
    -   Takes a date (YYYY-MM-DD)
    -   Fetches grouped daily bars from Polygon
    -   Inserts rows into `daily_bars`
-   **`transform_data.py`**:
    -   Takes the same date (YYYY-MM-DD)
    -   Finds the last available trading date before it
    -   Computes `daily_return = (close(t) - close(t-1)) / close(t-1)` for each ticker
    -   Updates the `daily_return` column in `daily_bars`

### 3. Backfill Historical Data

#### 3.1 `backfill_polygon.sh`

```bash
#!/usr/bin/env bash
# backfill_polygon.sh

START_DATE="2025-01-01"
END_DATE="2025-01-31"

CURRENT_DATE="$START_DATE"

while [ "$CURRENT_DATE" != "$END_DATE" ]; do
  echo "Ingesting data for: $CURRENT_DATE"
  python scripts/ingest_polygon.py "$CURRENT_DATE"

  # Increment the date by one day (macOS syntax)
  CURRENT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$CURRENT_DATE" "+%Y-%m-%d")
done

echo "Backfill complete!"
```

Usage:

```bash
cd scripts
chmod +x backfill_polygon.sh
./backfill_polygon.sh
```

#### 3.2 `backfill_daily_return.sh`

```bash
#!/usr/bin/env bash
# backfill_daily_return.sh

START_DATE="2025-01-01"
END_DATE="2025-01-31"

CURRENT_DATE="$START_DATE"

while [ "$CURRENT_DATE" != "$END_DATE" ]; do
  echo "Transform data for: $CURRENT_DATE"
  python scripts/transform_data.py "$CURRENT_DATE"

  # Increment the date by one day
  CURRENT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$CURRENT_DATE" "+%Y-%m-%d")
done

echo "Backfill complete!"
```

Usage:

```bash
cd scripts
chmod +x backfill_daily_return.sh
./backfill_daily_return.sh
```

### 4. Model Training (Future)

In the future, you can add a `scripts/train_model.py` to:

-   Pull historical data from Postgres, including `daily_return`.
-   Train a forecasting or regression model.
-   Optionally schedule the training with a separate Airflow DAG.

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

**Happy coding and data engineering!** If you have any issues:

-   Check Airflow logs: `docker compose logs -f`
-   Verify your `.env` is set correctly
-   Confirm the date increment logic works on your macOS or Linux environment
