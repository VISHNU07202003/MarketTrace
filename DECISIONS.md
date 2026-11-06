# MarketTrace — Architecture Decision Records (ADRs)

## ADR 001: Standalone MarketTrace Repository vs Modifying DepGraph
- **Context:** Vishnu Padyala's prior project [DepGraph](https://github.com/VISHNU07202003/DepGraph) (commit `b89b347`, Litmus assessment) generated candidate tool-field dependencies between Composio tools.
- **Decision:** Establish MarketTrace as an independent repository (`V:\MASTER'S\MarketTrace_Antigravity_Prompt`). Leave the original DepGraph assessment intact. Adapt DepGraph's dependency graph philosophy to temporal calculation windows.
- **Consequences:** Protects the assessment deliverable from breaking changes while clearly attributing the origin of dependency thinking.

## ADR 002: Fixed-Point Integer Ticks over Floating-Point Arithmetic
- **Context:** Binary floating-point representation (`double`, `float`) introduces rounding errors (e.g., $60000.01 represented as `60000.00999999999`).
- **Decision:** Order book prices and sizes are represented as 64-bit signed integers (`price_ticks` where 1 tick = $0.01; `size_units` where 1 unit = 1 satoshi / 1e-8 BTC). Midpoint is calculated via integer division: `(best_bid + best_ask) / 2`.
- **Consequences:** Eliminates rounding differences between C++, Python, SQLite, and Snowflake. Guarantees bit-for-bit replay determinism across languages.

## ADR 003: 11-Sample Window for Rolling Volatility
- **Context:** Rolling volatility can be calculated with various window sizes, sampling cadences, and annualization factors.
- **Decision:** Freeze metric contract before tuning:
  - Sample cadence: 11 consecutive valid midpoint observations.
  - Return definition: 10 log returns $r_i = \ln(m_i / m_{i-1})$.
  - Formula: Sample standard deviation $s = \sqrt{\frac{1}{9}\sum_{i=1}^{10} (r_i - \bar{r})^2}$ (no annualization).
  - Missing observation policy: Any missing or invalid sample in the 11-point window immediately blocks the window and marks it `INCOMPLETE`. No silent forward-filling.
- **Consequences:** Clear, un-ambiguous mathematical test target for Python oracle, C++ engine, and SQL.

## ADR 004: Offline-First Relational Warehouse Emulation
- **Context:** Snowflake trial access has a ~$400 budget limit and requires active credentials.
- **Decision:** Build an offline SQLite relational emulator (`warehouse/local_warehouse.py`) that mirrors Snowflake's DDL, landing tables, and windowed SQL analytics. Make live Snowflake upload an on-demand, bounded operation (`warehouse/snowflake_runner.py`).
- **Consequences:** Reviewers can clone the repository and run all tests, queries, and benchmarks without needing Snowflake accounts or credentials.

## ADR 005: Separation of Current Book Recovery from Historical Gap Repair
- **Context:** Incoming feeds that experience a gap often resynchronize using a fresh exchange snapshot.
- **Decision:** Enforce the "Honest Recovery" rule:
  - A fresh snapshot resets the order book and makes the *current* book state `VALID`.
  - However, historical calculation windows covering the dropped interval remain `INCOMPLETE`.
  - Historical windows can only be transitioned to `VALID` (Revision 2) if the missing historical evidence is independently recovered in a controlled replay branch.
- **Consequences:** Prevents false claims of data recovery and provides a sound engineering foundation for data audits.
