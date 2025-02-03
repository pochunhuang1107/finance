CREATE TABLE IF NOT EXISTS daily_bars (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    trading_date DATE NOT NULL,
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4),
    volume BIGINT,
    daily_return NUMERIC(12, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);