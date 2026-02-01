CREATE TABLE IF NOT EXISTS price_snapshots (
    id SERIAL PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(50) NOT NULL,
    btc_usd DECIMAL(18, 2),
    eth_usd DECIMAL(18, 2),
    eur_rate DECIMAL(12, 6),
    gbp_rate DECIMAL(12, 6),
    jpy_rate DECIMAL(12, 6),
    raw_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_snapshots_fetched_at ON price_snapshots(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_source ON price_snapshots(source);

CREATE TABLE IF NOT EXISTS price_alerts (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    asset VARCHAR(20) NOT NULL,
    previous_price DECIMAL(18, 2) NOT NULL,
    current_price DECIMAL(18, 2) NOT NULL,
    change_pct DECIMAL(8, 4) NOT NULL,
    snapshot_id INTEGER REFERENCES price_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON price_alerts(created_at DESC);

CREATE TABLE IF NOT EXISTS execution_log (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100) UNIQUE NOT NULL,
    job_id VARCHAR(100) NOT NULL,
    scheduled_at TIMESTAMPTZ,
    fired_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_execlog_received_at ON execution_log(received_at DESC);
