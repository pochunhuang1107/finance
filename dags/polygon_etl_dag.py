import os
from datetime import datetime, timedelta, date
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import subprocess

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': [os.getenv("AIRFLOW__SMTP__SMTP_USER")],
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

# Daily schedule at 6 AM EST; set catchup=False to avoid backfilling all past days
with DAG(
    dag_id='polygon_etl_dag',
    default_args=default_args,
    description='Daily ingestion of Polygon grouped bars into Postgres',
    start_date=datetime(2025, 2, 12),
    schedule_interval='0 11 * * *', # adjusted to 11 AM UTC (equivalent to 6 AM EST)
    catchup=False,
    tags=['ETL', 'Polygon']
) as dag:

    def run_ingestion(ti):
        """
        This function calls our Python script `ingest_polygon.py` 
        with yesterday's date (YYYY-MM-DD) as an argument.
        """
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Path where your scripts folder is mounted in the Airflow container
        script_path = "/opt/airflow/scripts/ingest_polygon.py"

        cmd = ["python", script_path, yesterday]
        print(f"Running command: {cmd}")

        # Run the ingestion script
        subprocess.run(cmd, check=True)  # Raises an error if script fails
        ti.xcom_push(key="ingested_date", value=yesterday)

    ingestion_task = PythonOperator(
        task_id='run_polygon_ingestion',
        python_callable=run_ingestion
    )

    def run_transform(ti):
        """
        Compute daily returns for the same date used in ingestion_task.
        """
        ingested_date = ti.xcom_pull(task_ids='run_polygon_ingestion', key="ingested_date")
        if not ingested_date:
            raise ValueError("No ingested_date found in XCom!")

        transform_script = "/opt/airflow/scripts/transform_data.py"

        cmd = ["python", transform_script, ingested_date]
        print(f"Running transform command: {cmd}")
        subprocess.run(cmd, check=True)

    transform_task = PythonOperator(
        task_id='transform_daily_returns',
        python_callable=run_transform
    )

    # Pipeline
    ingestion_task >> transform_task