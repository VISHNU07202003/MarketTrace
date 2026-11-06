-- MarketTrace Historical Analytical Queries
-- Computes Best Bid/Ask, Midpoints, Spreads, and 11-observation Rolling Volatilities

-- 1. Checkpoint Summary View
CREATE OR REPLACE VIEW v_book_metrics AS
SELECT 
    checkpoint_id,
    run_id,
    delivery_id,
    timestamp_ns,
    best_bid_ticks,
    best_ask_ticks,
    midpoint_ticks,
    spread_ticks,
    (spread_ticks::FLOAT / NULLIF(midpoint_ticks, 0)) * 10000.0 AS spread_bps,
    book_state
FROM book_checkpoints;

-- 2. Rolling Volatility Calculation (Window of 11 consecutive 1-second sample midpoints)
-- With 10 log returns: r_i = LN(m_i / m_{i-1})
-- Sample standard deviation: SQRT( SUM((r_i - mean)^2) / 9 )
WITH sampled_points AS (
    SELECT 
        checkpoint_id,
        run_id,
        delivery_id,
        timestamp_ns,
        midpoint_ticks,
        book_state,
        ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY timestamp_ns) AS sample_seq
    FROM book_checkpoints
    WHERE book_state = 'VALID' AND midpoint_ticks IS NOT NULL
),
lagged_points AS (
    SELECT 
        s.run_id,
        s.sample_seq,
        s.timestamp_ns AS window_end_ns,
        s.midpoint_ticks,
        LAG(s.midpoint_ticks, 1) OVER (PARTITION BY s.run_id ORDER BY s.sample_seq) AS prev_midpoint
    FROM sampled_points s
),
returns_stream AS (
    SELECT 
        run_id,
        sample_seq,
        window_end_ns,
        LN(midpoint_ticks::FLOAT / prev_midpoint::FLOAT) AS log_return
    FROM lagged_points
    WHERE prev_midpoint IS NOT NULL AND prev_midpoint > 0 AND midpoint_ticks > 0
),
window_stats AS (
    SELECT 
        run_id,
        sample_seq,
        window_end_ns,
        COUNT(log_return) OVER (PARTITION BY run_id ORDER BY sample_seq ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS return_count,
        AVG(log_return) OVER (PARTITION BY run_id ORDER BY sample_seq ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS mean_return,
        -- Calculate sample stddev across the 10 returns in the 11-point window
        SQRT(
            SUM(POWER(log_return - (AVG(log_return) OVER (PARTITION BY run_id ORDER BY sample_seq ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)), 2))
            OVER (PARTITION BY run_id ORDER BY sample_seq ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) / 9.0
        ) AS rolling_volatility
    FROM returns_stream
)
SELECT 
    run_id,
    window_end_ns,
    CASE 
        WHEN return_count = 10 THEN 'VALID'
        ELSE 'INCOMPLETE'
    END AS status,
    CASE 
        WHEN return_count = 10 THEN rolling_volatility
        ELSE NULL
    END AS numeric_value
FROM window_stats;
