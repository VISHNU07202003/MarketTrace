-- MarketTrace Teardown and Resource Protection Script
-- Ensures zero idle credit consumption

USE WAREHOUSE markettrace_wh;

-- Immediately suspend the warehouse
ALTER WAREHOUSE markettrace_wh SUSPEND;

-- Clean up staged files to prevent storage charges
REMOVE @markettrace_stage;

-- Drop stage
DROP STAGE IF EXISTS markettrace_stage;

-- (Optional) If full destruction is requested:
-- DROP WAREHOUSE IF EXISTS markettrace_wh;
-- DROP DATABASE IF EXISTS markettrace_db;
