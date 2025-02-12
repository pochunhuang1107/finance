CREATE TABLE IF NOT EXISTS ingestion_logs (
    run_id SERIAL PRIMARY KEY,
    run_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingestion_date DATE NOT NULL,
    row_count INT,
    duration_seconds NUMERIC(10,2)
);