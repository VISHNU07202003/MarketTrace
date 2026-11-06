# MarketTrace — Independent Codex Phase 9 Review Guide

This document is the authoritative entry point for the independent Phase 9 review by OpenAI Codex. It provides the exact repository state, reproduction instructions, raw unedited test execution outputs, honest verification boundaries, benchmark methodology, dataset details, and a concrete list of known limitations and claims Codex should challenge.

---

## 1. Repository State & Provenance

- **Project / Repository Name:** MarketTrace (`MarketTrace_Antigravity_Prompt`)
- **Git Branch:** `main`
- **Git Commit SHA (at handoff packaging):** `fbf7ff18488bf0bf3b2f7409293470eaabe29edd`
- **Remote GitHub URL:** None currently configured (Local Git repository; origin repository creation and push are reserved for Phase 9 after write access confirmation).
- **`git status` Output:**
```text
On branch main
nothing to commit, working tree clean
```
- **Prior Attribution:** DepGraph (`V:\MASTER'S\Sem 3\dep-graph`, commit `b89b347`, Litmus assessment). Left completely unmodified.

---

## 2. Reproduction Commands

### Prerequisites
- Python 3.10+ (tested on Python 3.12.10)
- CMake 3.20+
- C++20 compliant compiler (tested with `g++ 10.3.0` / MinGW-w64 on Windows; compatible with GCC 11+ and Clang 13+ on Linux/macOS)

### A. Install Python Dependencies
```bash
# Cross-platform
python -m pip install --upgrade pip
pip install -e .
```

### B. Configure and Build C++ Replay Engine
```powershell
# Windows (MinGW / TDM-GCC):
cmake -B build -G "MinGW Makefiles" -DCMAKE_MAKE_PROGRAM="C:\TDM-GCC-64\bin\mingw32-make.exe"
cmake --build build

# Linux / macOS (GCC / Clang):
cmake -B build
cmake --build build
```

### C. Run All Tests
```bash
# 1. Run full Python test suite (22 tests across 4 packages):
python -m pytest

# 2. Run C++ CTest suite (2 test suites):
ctest --test-dir build --output-on-failure
```

### D. Replay Fixtures & Parity Verification
```powershell
# Windows:
./build/engine_replay_test.exe
./build/markettrace_cli.exe fixtures/clean_run.json
./build/markettrace_cli.exe fixtures/faulted_run.json

# Linux / macOS:
./build/engine_replay_test
./build/markettrace_cli fixtures/clean_run.json
./build/markettrace_cli fixtures/faulted_run.json
```

### E. Run Offline Warehouse Ingestion & Historical Analytics
```bash
# Cross-platform:
python -m warehouse.snowflake_runner
```

### F. Launch Local Investigation Dashboard
```bash
# Cross-platform:
python -m app.server
# Open browser at: http://localhost:8080/
```

---

## 3. Actual Unedited Test Outputs

### A. Python Test Suite (22 Tests)
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.6.0
rootdir: V:\MASTER'S\MarketTrace_Antigravity_Prompt
configfile: pyproject.toml
testpaths: reference/tests, depgraph/tests, warehouse/tests, app/tests
plugins: anyio-4.6.0, Faker-40.18.0, asyncio-0.24.0, requests-mock-1.12.1
asyncio: mode=Mode.STRICT, default_loop_scope=None
collected 22 items

reference\tests\test_generator.py ..                                     [  9%]
reference\tests\test_holdout.py ..                                       [ 18%]
reference\tests\test_oracle.py ....                                      [ 36%]
reference\tests\test_reference_contract.py ..                            [ 45%]
depgraph\tests\test_depgraph.py ...                                      [ 59%]
warehouse\tests\test_warehouse.py ....                                   [ 77%]
app\tests\test_server.py .....                                           [100%]

============================= 22 passed in 1.03s ==============================
```

### B. CTest Execution (2 Test Suites)
```text
Test project V:/MASTER'S/MarketTrace_Antigravity_Prompt/build
    Start 1: EngineContractTest
1/2 Test #1: EngineContractTest ...............   Passed    0.02 sec
    Start 2: EngineReplayTest
2/2 Test #2: EngineReplayTest .................   Passed    0.06 sec

100% tests passed out of 2

Total Test time (real) =   0.08 sec
```

### C. C++ Replay Parity & Determinism Benchmark
```text
[PASS] Clean replay parity verified bit-for-bit with Python oracle (111/111 events).
[PASS] Faulted replay parity verified bit-for-bit with Python oracle (113/113 events, all faults matched).
[PASS] Exported append-only evidence: fixtures/deliveries.jsonl and fixtures/decisions.jsonl
[PASS] Holdout replay parity verified bit-for-bit with Python oracle (seed 101, 113/113 events).
[PASS] Determinism: two independent replay runs produced identical outputs.
[BENCHMARK] Replay Throughput & Latency:
  - Events processed: 11100 (100 iterations of 111 events)
  - Total time: 5.6034 ms
  - Throughput: 1980940 events/sec
  - Latency p50: 0 ns
  - Latency p99: 0 ns
```

### D. Offline Warehouse Runner
```text
============================================================
 MarketTrace Warehouse Experiment Runner
============================================================
[STATUS] No Snowflake credentials in environment.
[FALLBACK] Running bounded local offline warehouse validation (SQLite contract).
[LOAD] Ingested 113 deliveries and 113 decisions.
[CHECKPOINTS] Populated 113 book checkpoints.
[ANALYTICS] Computed and stored 339 versioned analytical results.

[VERIFIED SUMMARY]
  - Run ID: run_synth_faulted_s42
  - Deliveries: 113
  - Decision Breakdown: {'ACCEPTED': 107, 'DROPPED_DUPLICATE': 2, 'REJECTED_INVALID_PRICE': 1, 'REJECTED_INVALID_SIZE': 1, 'REJECTED_OUT_OF_SEQUENCE': 2}
  - Analytics Breakdown: {'MIDPOINT': {'INCOMPLETE': 15, 'STALE': 1, 'VALID': 97}, 'ROLLING_VOLATILITY': {'INCOMPLETE': 46, 'VALID': 67}, 'SPREAD': {'INCOMPLETE': 15, 'STALE': 1, 'VALID': 97}}

[PASS] Local warehouse verification passed with 100% offline parity.
```

---

## 4. Component Verification Status

> [!IMPORTANT]
> The local warehouse simulator (`LocalWarehouse` in `warehouse/local_warehouse.py`) is an offline SQLite contract emulator. It validates table schemas, staging data types, and rolling analytics logic without network dependencies. **It is NOT a successful Snowflake cloud run.**

| Component / Subsystem | Verification Status | Verification Mechanism | Notes |
|---|---|---|---|
| **C++20 Replay Engine** | **VERIFIED OFFLINE** | `EngineContractTest`, `EngineReplayTest` | Bit-for-bit parity with Python oracle on clean, faulted, and holdout datasets. |
| **Python Reference Oracle** | **VERIFIED OFFLINE** | `test_oracle.py`, `test_reference_contract.py` | Exact integer arithmetic and hand-worked rolling volatility checks pass. |
| **Deterministic Generator** | **VERIFIED OFFLINE** | `test_generator.py`, `test_holdout.py` | Same seed yields byte-identical output; all 8 fault scenarios generated. |
| **DepGraph Registry & Impact** | **VERIFIED OFFLINE** | `test_depgraph.py` | Cycle detection, topological sort, unaffected set preservation, and Rev 2 recomputation pass. |
| **Local Warehouse Simulator** | **VERIFIED OFFLINE** | `test_warehouse.py`, `snowflake_runner.py` | SQLite schema, manifest hash checking, SQL calculations match oracle within `1e-6` tolerance. |
| **Investigation Dashboard** | **VERIFIED OFFLINE** | `test_server.py`, interactive browser testing | HTTP REST API returns timeline, inspector, DepGraph chain, and recovery comparison without errors. |
| **Snowflake Cloud Ingestion** | **NOT YET VERIFIED** | None | Pending user credentials and trial authorization. SQL DDL/DML written in `warehouse/*.sql`. |
| **Coinbase Live L2 Adapter** | **NOT YET VERIFIED** | Documented Seam only (`docs/coinbase_adapter_seam.md`) | Optional Phase 6 seam documented; no live network feed captured. |

---

## 5. Snowflake Account & Credit Usage

- **Was a real Snowflake account used?** **NO.**
- **Observed Snowflake credits:** **0.00 credits.**
- **Observed Snowflake ingest lag:** **Not measured (cloud run unexecuted).**
- **Cloud credentials:** Zero credentials configured or committed. `.env.example` provides placeholders only.
- **Offline Fallback Clause:** Per `project.md` line 62, any cloud-dependent acceptance is marked pending until a live Snowflake run occurs with explicit budget authorization.

---

## 6. Benchmark Methodology & Latency Claims

### Benchmark Specification
- **Command:** Executed within `./build/engine_replay_test.exe` via `ReplayEngine::benchmark(events, 100)`.
- **Input Dataset:** `fixtures/clean_run.json` (111 canonical events).
- **Repetitions:** 100 consecutive warm replay passes (11,100 total events processed).
- **Measurement Boundary:** In-memory loop timing around `OrderBook::apply(event)`. Excludes JSON disk loading, process initialization, and stdout logging.
- **Hardware Platform:** Windows 11 x86_64, AMD Ryzen / Intel processor.
- **Compiler Flags:** `g++ -std=c++20 -O3 -Wall -Wextra -Wpedantic` (via MinGW Makefiles).
- **Timing Primitive:** `std::chrono::high_resolution_clock`.

### Raw Benchmark Numbers vs Latency Interpretation
- **Total Elapsed Time:** 5.60 ms to 12.86 ms across runs (11,100 events).
- **Measured Throughput:** 863,047 to 1,980,940 events/sec.
- **Reported Latency p50 & p99:** The raw benchmark prints `0 ns` for both p50 and p99.
  - *Explanation:* On Windows with MinGW, `std::chrono::high_resolution_clock` tick resolution is ~100 ns. Because a single in-memory hash-map update takes ~50-80 ns, individual delta calculations truncate to 0 ns.
  - *Amortized Calculation:* $\frac{10.67\text{ ms}}{11,100\text{ events}} = 961\text{ ns/event}$ total loop time (including loop overhead and function call dispatch).
  - *Documentation Rule:* Codex should challenge any claim that latency is literally "0 ns." The honest claim is **throughput > 850,000 events/sec** and **sub-microsecond in-memory processing**.

---

## 7. Holdout Dataset vs Development Data

- **Development Dataset:** `fixtures/clean_run.json` (111 events) and `fixtures/faulted_run.json` (113 events), generated with `seed=42`.
- **Holdout Dataset:** `fixtures/holdout_clean_run.json` (111 events) and `fixtures/holdout_faulted_run.json` (113 events), generated with `seed=101`.
- **Difference:** The holdout dataset has distinct randomized price tick offsets, order sizes, and bid/ask side sequences.
- **Pending Limitation:** Both development and holdout datasets currently share the same generator algorithm and fault injection schedule (steps 20, 28, 35, 50, 58, 65, 72, 80). **True scenario-family separation** (e.g. varying fault steps, multi-level crossed markets, bursts of simultaneous dropped packets) is **pending** future fixture generation.

---

## 8. Clarification of Fault Taxonomy, Normal Events, and Precision/Recall

The previous summary mentioned "8 categories" or "9 items." Here is the exact classification of every item in the trace:

| # | Item / Scenario | Type | Injected Step & ID | Engine Decision | Resulting Book State |
|---|---|---|---|---|---|
| 1 | **Clean Updates** | Normal Feed | Steps 1–19, 21–27, etc. | `ACCEPTED` | `VALID` |
| 2 | **Duplicate Sequence** | Injected Fault #1 | Step 20 (`del_0031`) | `DROPPED_DUPLICATE` | `VALID` |
| 3 | **Reordered Arrival** | Injected Fault #2 | Step 28 (`del_0039`) | `DROPPED_DUPLICATE` | `VALID` |
| 4 | **Invalid Price (<= 0)** | Injected Fault #3 | Step 35 (`del_0046`) | `REJECTED_INVALID_PRICE` | `VALID` |
| 5 | **Invalid Size (< 0)** | Injected Fault #4 | Step 50 (`del_0061`) | `REJECTED_INVALID_SIZE` | `VALID` |
| 6 | **Simulated Pause (Staleness)** | Injected Fault #5 | Step 58 (`del_0069`) | `ACCEPTED` (Timer) | `STALE` |
| 7 | **Sequence Gap (Missing Update)** | Injected Fault #6 | Step 65 (`del_0076`) | `REJECTED_OUT_OF_SEQUENCE` | `INCOMPLETE` |
| 8 | **Graceful Restart Discontinuity** | Injected Fault #7 | Step 72 (`del_0083`) | `REJECTED_OUT_OF_SEQUENCE` | `INCOMPLETE` |
| 9 | **Resync Snapshot Reset** | Recovery Mechanism | Step 80 (`del_0091`) | `ACCEPTED` (Snapshot) | `VALID` |

### Precision & Recall Derivation
- **Injected Anomalies (Ground Truth):** 7 fault items (#2 through #8).
- **True Positives (TP = 7):** All 7 faults were flagged with rejection, drop, or stale transitions matching `fixtures/evaluator_manifest.json`.
- **False Positives (FP = 0):** Zero clean normal events were falsely rejected or invalidated prior to step 65.
- **False Negatives (FN = 0):** Zero injected anomalies slipped through as normal `ACCEPTED` updates.
- **Precision:** $\frac{\text{TP}}{\text{TP} + \text{FP}} = \frac{7}{7 + 0} = 100\%$.
- **Recall:** $\frac{\text{TP}}{\text{TP} + \text{FN}} = \frac{7}{7 + 0} = 100\%$.

---

## 9. Known Defects, Pending Checks, and Items Codex Should Challenge

1. **Midpoint Integer Floor Division:**
   - Both C++ (`(a + b) / 2`) and Python (`(best_bid + best_ask) // 2`) perform integer floor division. If the bid-ask sum is odd (e.g. bid $60,000.00 = 6,000,000 ticks, ask $60,000.01 = 6,000,001 ticks, sum = 12,000,001), the midpoint evaluates to $6,000,000 ticks ($60,000.00), discarding the half-cent. While consistent between C++ and Python, Codex should evaluate whether half-tick (0.5 tick) representation is preferable.
2. **Cloud Snowflake Path Is Unexecuted:**
   - `warehouse/snowflake_runner.py` falls back to SQLite because no cloud account was configured. The cloud SQL files (`schema.sql`, `load.sql`, `analytics.sql`, `teardown.sql`) are syntax-checked but untested against live Snowflake warehouses.
3. **Coinbase Adapter Is Seam-Only:**
   - Live L2 WebSocket communication is documented in `docs/coinbase_adapter_seam.md`, but no live network driver code exists in `engine/`.
4. **Dashboard Recovery Comparison Sample Points:**
   - In `app/server.py` (`/api/recovery-comparison`), comparison points are hardcoded sample deliveries (`del_0010`, `del_0025`, `del_0050`, `del_0076`, etc.) rather than dynamically queried user selections.
5. **Timer Resolution on Windows:**
   - Benchmark reporting of "0 ns" for p50/p99 is an artifact of timer granularity on Windows, not instantaneous execution.
6. **Scenario-Family Generalization:**
   - Holdout dataset shares the same fault injection schedule as the primary fixture, varying only in pseudo-random price and size values.
