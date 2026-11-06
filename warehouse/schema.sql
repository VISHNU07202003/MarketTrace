-- MarketTrace Versioned Relational Schema
-- Compatible with Snowflake DDL and SQLite local offline runner

CREATE TABLE IF NOT EXISTS run_manifests (
    run_id VARCHAR(64) PRIMARY KEY,
    seed INT,
    input_hash VARCHAR(64),
    fault_manifest_hash VARCHAR(64),
    calculation_version VARCHAR(32),
    status VARCHAR(32),  -- CREATED, LOADED, ANALYZED, FAILED
    created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_deliveries (
    run_id VARCHAR(64) NOT NULL,
    delivery_id VARCHAR(64) PRIMARY KEY,
    source VARCHAR(64),
    source_session VARCHAR(64),
    instrument VARCHAR(32),
    message_kind VARCHAR(32),
    provider_sequence BIGINT,
    receive_time_ns BIGINT NOT NULL,
    replay_time_ns BIGINT NOT NULL,
    side VARCHAR(16),
    price_ticks BIGINT,
    size_units BIGINT,
    payload_hash VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS processing_decisions (
    delivery_id VARCHAR(64) PRIMARY KEY,
    code VARCHAR(64) NOT NULL,  -- ACCEPTED, REJECTED_INVALID_PRICE, REJECTED_OUT_OF_SEQUENCE, etc.
    reason TEXT,
    decision_time_ns BIGINT NOT NULL,
    resulting_book_state VARCHAR(32) NOT NULL  -- VALID, STALE, INCOMPLETE, BLOCKED
);

CREATE TABLE IF NOT EXISTS book_checkpoints (
    checkpoint_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    delivery_id VARCHAR(64) NOT NULL,
    timestamp_ns BIGINT NOT NULL,
    best_bid_ticks BIGINT,
    best_ask_ticks BIGINT,
    midpoint_ticks BIGINT,
    spread_ticks BIGINT,
    is_crossed BOOLEAN,
    is_empty BOOLEAN,
    book_state VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS analytical_results (
    result_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,  -- MIDPOINT, SPREAD, ROLLING_VOLATILITY
    window_start_ns BIGINT,
    window_end_ns BIGINT,
    revision INT DEFAULT 1,
    status VARCHAR(32) NOT NULL,       -- VALID, STALE, INCOMPLETE, BLOCKED, RECOMPUTING
    numeric_value DOUBLE PRECISION,
    evidence_deliveries TEXT,          -- JSON array or comma-separated delivery IDs
    calculation_version VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    delivery_id VARCHAR(64) NOT NULL,
    fault_type VARCHAR(64) NOT NULL,
    detected_at_ns BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,       -- OPEN, RESUMED_WITH_GAP, RECOVERED_AUTHORITATIVE, UNRESOLVED
    details TEXT
);
