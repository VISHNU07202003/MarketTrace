-- MarketTrace Bounded Snowflake Staging and Ingestion Script
-- Enforces budget ceiling and resource monitor discipline

-- 1. Create Resource Monitor with strict credit limit (Max $400 trial budget ceiling)
CREATE OR REPLACE RESOURCE MONITOR markettrace_monitor
    WITH CREDIT_QUOTA = 5
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS 
        ON 80 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND;

-- 2. Create X-Small Warehouse with auto-suspend after 60 seconds
CREATE OR REPLACE WAREHOUSE markettrace_wh
    WITH WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    RESOURCE_MONITOR = markettrace_monitor
    INITIALLY_SUSPENDED = TRUE;

USE WAREHOUSE markettrace_wh;

-- 3. Create Database & Schema
CREATE DATABASE IF NOT EXISTS markettrace_db;
USE DATABASE markettrace_db;
CREATE SCHEMA IF NOT EXISTS markettrace_schema;
USE SCHEMA markettrace_schema;

-- 4. Create Named Internal Stage for Bounded Uploads
CREATE OR REPLACE STAGE markettrace_stage
    FILE_FORMAT = (TYPE = JSON);

-- 5. Staged File Upload Commands (Executed via Snowflake SnowSQL / Python Connector)
-- PUT file://fixtures/deliveries.jsonl @markettrace_stage/run_01/ AUTO_COMPRESS=TRUE;
-- PUT file://fixtures/decisions.jsonl @markettrace_stage/run_01/ AUTO_COMPRESS=TRUE;

-- 6. Bounded COPY INTO Statements
COPY INTO raw_deliveries (
    run_id, delivery_id, source, source_session, instrument,
    message_kind, provider_sequence, receive_time_ns, replay_time_ns,
    side, price_ticks, size_units, payload_hash
)
FROM (
    SELECT 
        $1:run_id::VARCHAR,
        $1:delivery_id::VARCHAR,
        $1:source::VARCHAR,
        $1:source_session::VARCHAR,
        $1:instrument::VARCHAR,
        $1:message_kind::VARCHAR,
        $1:provider_sequence::BIGINT,
        $1:receive_time_ns::BIGINT,
        $1:replay_time_ns::BIGINT,
        $1:side::VARCHAR,
        $1:price_ticks::BIGINT,
        $1:size_units::BIGINT,
        $1:payload_hash::VARCHAR
    FROM @markettrace_stage/run_01/deliveries.jsonl.gz
);

COPY INTO processing_decisions (
    delivery_id, code, reason, decision_time_ns, resulting_book_state
)
FROM (
    SELECT 
        $1:delivery_id::VARCHAR,
        $1:code::VARCHAR,
        $1:reason::VARCHAR,
        $1:decision_time_ns::BIGINT,
        $1:resulting_book_state::VARCHAR
    FROM @markettrace_stage/run_01/decisions.jsonl.gz
);

-- 7. Verification / Publication Integrity Check
SELECT 
    d.run_id,
    COUNT(d.delivery_id) AS total_deliveries,
    COUNT(p.delivery_id) AS total_decisions,
    SUM(CASE WHEN p.code = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_count,
    SUM(CASE WHEN p.code != 'ACCEPTED' THEN 1 ELSE 0 END) AS rejected_count
FROM raw_deliveries d
LEFT JOIN processing_decisions p ON d.delivery_id = p.delivery_id
GROUP BY d.run_id;
