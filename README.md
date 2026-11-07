# MarketTrace

A reproducible, **synthetic** BTC-USD order-book incident study. It asks a practical question: when a market update disappears, which current quotes and historical calculations can we still trust?

## Problem and case study

An order-book stream advances by sequence number. If update `inc_0060` disappears and `inc_0061` arrives, a consumer that simply continues may report plausible but unsupported prices and rolling risk measures. A later snapshot can establish a usable **current** book; it does not recreate the missing history.

The fixture holds back one generated update at second 60. The C++ replay rejects the next update and labels the book `INCOMPLETE` until a synthetic snapshot reset plus bid and ask rebuild it at second 80. Historical 11-sample volatility windows remain incomplete through that gap; after 11 uninterrupted valid one-second update samples, a new window at second 91 becomes valid. A separate controlled branch puts the exact withheld event back into its original position and recalculates its results. For example:

| Window ending | Complete branch | Damaged branch | Repaired branch |
|---|---|---|---|
| `inc_0059` | VALID | VALID | VALID |
| `inc_0060` | VALID | MISSING | VALID |
| `inc_0061` | VALID | INCOMPLETE | VALID |
| `inc_0079` | VALID | INCOMPLETE | VALID |
| `inc_0081` | INCOMPLETE (new sample window) | INCOMPLETE | INCOMPLETE |
| `inc_0091` | VALID | VALID | VALID |

The displayed volatility is the sample standard deviation of **10 log returns from 11 one-second midpoint observations**, with no forward filling. It is not a trading signal. Midpoints retain half-tick precision; one price tick is $0.01 in this fixture. This is a controlled synthetic demonstration, not proof about exchange feeds or a production order book.

## Components and provenance

- `reference/`: Python oracle and deterministic generators, including the retained event and clean/damaged/repaired incident fixtures. The holdout varies seed and prices, but uses the same fault schedule; it is not a new scenario family.
- `engine/`: C++20 sequence checks, book state, snapshots, replay decisions, and JSON output. Rejection of malformed or missing updates blocks incremental updates until a complete snapshot. C++ and Python agree on the checked fixture decisions and metrics; common specification errors remain possible.
- `warehouse/`: SQLite stores evidence, engine/reference checkpoints, and locally computed midpoint, spread, and rolling volatility. Checkpoints are replay outputs, so comparing SQLite midpoints with those same inputs does **not** independently validate book reconstruction. A separate formula check validates selected volatility windows. The Snowflake SQL files are **unverified drafts**; the cloud runner explicitly stops if credentials are present rather than claiming a cloud run.
- `depgraph/`: typed, temporal dependency graph adapted from the idea of [Vishnu's DepGraph](https://github.com/VISHNU07202003/DepGraph). It explains impact and produces a topological recomputation **plan**. Persisted revision-2 results and a measured minimal-cost recomputation are not implemented.
- `app/`: local dashboard for run overview, event/decision/lineage inspection, and calculated branch comparison. It labels whether displayed replay records came from the C++ CLI or the Python reference; SQLite calculations are always local.

## Run it locally

Prerequisites: Python 3.10+, a C++20 compiler, and CMake 3.20+ for the standard build. From the repository root:

```sh
python -m pip install -e .
python -m pytest -q
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
./build/markettrace_cli fixtures/incident_damaged.json --output runs/incident_damaged_engine.json
python -m warehouse.snowflake_runner
python -m app.server
```

Open `http://127.0.0.1:8080`. Without CLI-generated `runs/` output, the dashboard labels and uses the bundled Python reference records. The runner refuses stale engine output that differs from the reference fixture. On Windows, the CLI binary may have an `.exe` suffix. Do not set Snowflake credentials for this offline demo.

To regenerate fixtures (this changes the checked-in expected files), run `python -m reference.generator` and `python -m reference.incident`, then rebuild and rerun the tests. See [CODEX_PHASE9_AUDIT.md](CODEX_PHASE9_AUDIT.md) for this review's exact environment, test commands, findings, and remaining gates.

## What this demonstrates and what remains

The useful engineering idea is an **explainable fault investigation across event processing, data quality, historical windows, and UI**. This is a credible small portfolio project when presented as an offline prototype. It is not a novel market-data algorithm, a trading engine, an FPGA project, a benchmarked low-latency product, or a verified Snowflake integration. Snowflake ingestion, a real feed adapter, independent scenario-family holdouts, durable revisioned recomputation, and a credible large-sample performance study remain future work. No hiring outcome or superiority over Snowflake's native tooling is implied.
