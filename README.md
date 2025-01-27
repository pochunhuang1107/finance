## Finance Data Engineering & ML Project

This repository hosts a **real-time stock data pipeline** and **time-series ML** components. It’s part of a broader learning path that combines data engineering technologies (Kafka, PySpark, Docker, Airflow) with machine learning (TensorFlow, LSTM networks).

---

### Table of Contents

1. [Project Overview](#project-overview)
2. [Requirements](#requirements)
3. [Setup Instructions](#setup-instructions)
4. [Directory Structure](#directory-structure)
5. [Usage](#usage)

---

## Project Overview

**Current Status**:

-   **Environment**: A Python virtual environment is set up with `pandas`, `requests`, etc.
-   **Docker**: We use `docker-compose` to run **Kafka**, **Zookeeper**, **Spark** (master & worker), and **PostgreSQL** containers.
-   **Polygon API**: We fetch **daily grouped stock data** (OHLC, volume, etc.) for a specific date. The data is then loaded into a `pandas` DataFrame for further analysis or storage.

---

## Requirements

1. **Python 3.9+**
    - We tested with Python 3.11 on macOS (M1).
2. **Docker & Docker Compose**
    - Docker Desktop for Apple Silicon.
3. **Polygon.io API Key**
    - Sign up at [Polygon.io](https://polygon.io/) for your key.
    - Make sure your plan supports the endpoints you need.
4. **Optional**: PostgreSQL client tools or GUIs (e.g., pgAdmin) if you want to interact with the database directly.

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/pochunhuang1107/finance.git
cd finance
```

### 2. Create and Activate a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

(Optional) Install base dependencies:

```bash
pip install requests pandas
pip freeze > requirements.txt
```

### 3. Configure Docker Compose

Inside the `docker` folder, there’s a `docker-compose.yml` that starts:

-   **Zookeeper** (for Kafka)
-   **Kafka**
-   **Spark Master** and **Spark Worker** (Bitnami images)
-   **PostgreSQL** (as our database)

From the `docker` directory:

```bash
cd docker
docker compose up -d
```

---

## Directory Structure

Below is our current layout:

```
finance
├── docker
│   └── docker-compose.yml
├── data
│   ├── raw
│   └── processed
├── notebooks
├── scripts
│   └── stock_data_test.py
├── venv
├── .gitignore
├── requirements.txt
└── README.md
```

**Key Directories**:

-   **`docker/`**: Docker-related configurations (Kafka, Spark, PostgreSQL).
-   **`data/`**: Stores raw and processed data.
-   **`scripts/`**: Python scripts for data ingestion or processing (e.g., `stock_data_test.py` uses the Polygon API).
-   **`notebooks/`**: Place Jupyter notebooks for EDA or quick experiments.
-   **`venv/`**: Your Python virtual environment (excluded from Git).

---

**Longer-Term Plan**:

-   Integrate Airflow to schedule your Spark/Kafka jobs.
-   Develop an LSTM model for time-series forecasting with TensorFlow.
-   Deploy the pipeline on AWS or GCP for hands-on experience.

---

**Thank you for checking out this project!**
If you have questions, suggestions, or encounter issues, please open an issue or reach out directly. Contributions and pull requests are welcome as the project evolves.
