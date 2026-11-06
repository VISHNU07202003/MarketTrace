# MarketTrace — Handover & Phase Log

## Current State (Phase 0 Complete)

- **Workspace:** `V:\MASTER'S\MarketTrace_Antigravity_Prompt`
- **Git Branch:** `main` (clean standalone repository)
- **Toolchain Verified:**
  - Python 3.12.10 with `pytest 8.3.4`, `pydantic 2.10+`
  - C++20 with `g++ 10.3.0` (TDM-GCC-64)
  - CMake 4.4.4 with `mingw32-make`
- **Core Interfaces Established:**
  - Shared data envelope, decision codes, quality states defined identically in C++ (`engine/include/markettrace/envelope.hpp`) and Python (`reference/models.py`).
  - Order book state tracking (`engine/include/markettrace/order_book.hpp`, `engine/src/order_book.cpp`) with price validation, sequence gap detection, and snapshot resynchronization.
- **Repository Strategy Decision:**
  - Dedicated repository `MarketTrace` established. The prior `DepGraph` repository (`V:\MASTER'S\Sem 3\dep-graph`, commit `b89b347`) remains intact and unmodified to preserve the original Litmus assessment deliverable.
  - MarketTrace explicitly adapts DepGraph's dependency graph philosophy to temporal market data calculation windows.

## Verified Gate Commands & Outputs

### 1. C++ Engine Build and Contract Test
```powershell
cmake -B build -G "MinGW Makefiles" -DCMAKE_MAKE_PROGRAM="C:\TDM-GCC-64\bin\mingw32-make.exe"
cmake --build build
ctest --test-dir build --output-on-failure
./build/markettrace_cli.exe
```
**Output:**
```
Test project V:/MASTER'S/MarketTrace_Antigravity_Prompt/build
    Start 1: EngineContractTest
1/1 Test #1: EngineContractTest ...............   Passed    0.22 sec

100% tests passed out of 1
MarketTrace Engine v0.1.0 (C++20)
Order-book fault replay and impact verification core
Initialized book for BTC-USD, status: VALID
```

### 2. Python Reference Contract Test
```powershell
python -m pytest reference/tests/test_reference_contract.py
```
**Output:**
```
collected 2 items
reference\tests\test_reference_contract.py ..                            [100%]
============================== 2 passed in 1.04s ==============================
```

---

## Second Mind Review

```text
SECOND MIND REVIEW — phase 0, 2026-11-06, Self-Review (per mind.md protocol)
Observed state: Clean initial repo on branch main; CMake build and ctest EngineContractTest passed (1/1); pytest test_reference_contract.py passed (2/2); CLI executable ran with output.
Gate: PASS.
North-star fit: Establishes the canonical event envelope, book validity states, and integer tick scaling shared between C++ engine and Python reference, forming the foundation for the fault-to-recovery incident replay.
Mismatch or new fact: Verified local toolchain has g++ 10.3.0 and mingw32-make; CMake was installed locally via pip. DepGraph location confirmed at "V:\MASTER'S\Sem 3\dep-graph" (commit b89b347) and preserved intact.
Plan decision: KEEP. Phase 1 proceeds as planned in project.md.
Contract effects: Canonical EventEnvelope, ProcessingDecision, BookMetrics, and QualityState frozen in both C++ and Python models.
Open verification: Cloud Snowflake verification remains pending and strictly deferred to Phase 3; offline verification is 100% functional.
Next builder task: Implement Phase 1: deterministic Python fixture generator creating 1 snapshot and 100 updates with synthetic fault injection (sequence gap, invalid price/size, resync) and an independent reference oracle.
```

## Next Exact Step
Proceed to **Phase 1: Offline Reference and Fault Fixtures**:
Create `reference/oracle.py`, `reference/generator.py`, and test suites in `reference/tests/` to deterministically produce byte-identical BTC-USD fixture traces, fault manifests, and reference calculated metrics.
