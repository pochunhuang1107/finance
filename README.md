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
    - [2. Ingestion Scripts](#2-ingestion-scripts)
    - [3. Bulk Load / Backfill of Historical Data](#3-bulk-load--backfill-of-historical-data)
    - [4. Model Training (Future)](#4-model-training-future)
  - [License](#license)
  - [Contact](#contact)

---

## Project Overview

-   **Goal**: Collect daily stock market “grouped bars” from [Polygon.io](https://polygon.io/) for US stocks and store them in a Postgres database.
-   **Tooling**:
    -   **Airflow** for scheduling and orchestration.
    -   **PostgreSQL** for storing historical data.
    -   **Python** scripts for ingestion and ML tasks.
    -   **Docker Compose** for running Airflow + Postgres locally.
-   **Machine Learning**: Train a time-series or regression model using the historical data to predict future prices or trends.

## Architecture

1. **Data Source**: Polygon.io “Grouped Daily (Bars)” endpoint.
2. **ETL**:
    - Python script (`ingest_polygon.py`) to fetch data for a given date.
    - **Airflow DAG** (`polygon_etl_dag.py`) that runs the script daily.
3. **Database**: Postgres stores the data in a `daily_bars` table.
4. **ML**: (Future) A separate script or Airflow DAG pulls data from Postgres to train a predictive model.

A high-level architecture diagram might look like:

```
+-------------+            +-------------------+             +----------------+
| Polygon API |   --->     |  Airflow (DAG)    |    --->     |  PostgreSQL DB |
+-------------+            |  ingest_polygon   |             |  daily_bars    |
                           +-------------------+             +----------------+
                                     |
                                     v
                                 ML Training
```

## Directory Structure

```plaintext
finance/
├── dags/
│   ├── polygon_etl_dag.py        # Airflow DAG for daily ingestion
│   └── ml_training_dag.py        # (Future) Airflow DAG for ML training
├── scripts/
│   ├── test_polygon_api.py       # Quick script to fetch & print Polygon data
│   ├── ingest_polygon.py         # Main ingestion script
│   └── train_model.py            # (Future) Machine learning training
├── sql/
│   └── create_tables.sql         # SQL schema to create daily_bars table
├── docker-compose.yml            # Airflow + Postgres local setup
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (excluded from git)
└── README.md
```

> **Note**: The `.env` file is excluded from version control. See [Environment Variables (.env)](#2-environment-variables-env) below.

## Requirements

-   **Docker Desktop** (for Docker Compose)
-   **Python 3.9+** (optional if you want to run scripts locally rather than in Docker)
-   **Polygon.io** account & API key
-   **Git** (for version control)

## Setup

### 1. Clone the Repository

```bash
cd ~/Desktop/Project
git clone https://github.com/pochunhuang1107/finance.git
cd finance
```

### 2. Environment Variables (.env)

Create a `.env` file in the **same directory** as `docker-compose.yml` (not committed to Git). It should look like:

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

-   Keep this file out of source control to protect your credentials.
-   Make sure your `docker-compose.yml` references these variables in both the **airflow-webserver** and **airflow-scheduler** environments.

### 3. Docker Compose

Spin up Airflow and Postgres containers:

```bash
docker compose up -d
```

-   **Airflow UI** is accessible at [http://localhost:8080](http://localhost:8080).
-   **Postgres** listens on `localhost:5432` (though inside the containers, the host is `postgres`).

### 4. Database Setup

Initialize the `daily_bars` table in Postgres:

```bash
docker cp sql/create_tables.sql postgres:/tmp/create_tables.sql
docker exec -it postgres psql \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -f /tmp/create_tables.sql
```

Verify:

```bash
docker exec -it postgres psql \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -c "\dt"
```

You should see a table named `daily_bars`.

### 5. Test Polygon API Script

A simple script (`scripts/test_polygon_api.py`) fetches grouped daily bars for a given date and prints the first result:

```bash
cd ~/Desktop/Project/finance
pip install -r requirements.txt  # if running locally
export POLYGON_API_KEY=YOUR_POLYGON_API_KEY
python scripts/test_polygon_api.py
```

Check console output to ensure data is returned (e.g., “Number of tickers returned: 9405”).

## Usage

### 1. Airflow DAGs

Your primary Airflow DAG is `polygon_etl_dag.py`, which:

-   Schedules the ingestion script daily.
-   Fetches **yesterday’s** data and loads it into Postgres (by default at 6 AM).

#### Triggering DAG in Airflow

1. Go to [http://localhost:8080](http://localhost:8080).
2. Enable (unpause) the DAG named `polygon_etl_dag`.
3. Monitor tasks in the Airflow UI, view logs, and confirm successful runs.

### 2. Ingestion Scripts

-   **`scripts/ingest_polygon.py`**:
    1. Accepts a date (YYYY-MM-DD) as a command-line argument.
    2. Fetches data from Polygon.
    3. Inserts into `daily_bars` table in Postgres.

> **Example**:
>
> ```bash
> python scripts/ingest_polygon.py 2025-01-29
> ```
>
> This script can also be used manually to ingest specific dates, or in loops for backfilling.

### 3. Bulk Load / Backfill of Historical Data

If you need to populate data for a **range of historical dates**, you can:

**Use a Bash Loop** (one-off approach):

```bash
# backfill.sh

START_DATE="2024-01-01" # Adjust up to free/paid tier limit
END_DATE="2025-01-01"  # Adjust to the last missing date

CURRENT_DATE="$START_DATE"

while [ "$CURRENT_DATE" != "$END_DATE" ]; do
    echo "Ingesting data for: $CURRENT_DATE"
    python scripts/ingest_polygon.py "$CURRENT_DATE"

    # Increment the date by one day
    CURRENT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$CURRENT_DATE" "+%Y-%m-%d")
done

echo "Backfill complete!"
```

Then run:

```bash
cd scripts
chmod +x backfill.sh
./backfill.sh
```

This will insert data for each date in the range into `daily_bars`.

### 4. Model Training (Future)

-   **`scripts/train_model.py`** will connect to Postgres, load recent historical data, and train a baseline forecasting model.
-   You can create an Airflow DAG (`ml_training_dag.py`) if you want an automated schedule for retraining.

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

**Happy coding and data engineering!** If you have any issues, check:

-   The Airflow logs via `docker compose logs -f`
-   The Postgres container logs
-   Your `.env` configuration

and/or contact the maintainer.

```

```
