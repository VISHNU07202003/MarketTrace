# Changelog

All notable changes to MarketTrace are documented in this file.

## [0.1.0] - 2026-11-06 (Candidate for Codex Review)

### Added
- **Phase 0:**
  - Audited local toolchain (`g++ 10.3.0`, `CMake 4.4.4`, `Python 3.12.10`, `pytest 8.3.4`).
  - Defined canonical event envelope, quality states, and decision codes shared across C++ and Python.
  - Set up build manifests (`CMakeLists.txt`, `pyproject.toml`, `package.json`), `.editorconfig`, `.gitignore`, `.env.example`.
- **Phase 1:**
  - Independent Python reference oracle (`reference/oracle.py`) with exact midpoint, spread, and sample volatility math.
  - Deterministic fixture generator (`reference/generator.py`) producing byte-identical traces on seed 42.
  - Generated canonical fixture datasets: `clean_run.json` (111 events) and `faulted_run.json` (113 events).
  - Private evaluator manifest (`evaluator_manifest.json`) isolating injected fault positions.
- **Phase 2:**
  - C++20 replay engine (`engine/src/replay.cpp`, `engine/src/order_book.cpp`) utilizing `nlohmann/json.hpp`.
  - Achieved 100% bit-for-bit event-by-event parity against the Python reference oracle (111/111 clean, 113/113 faulted).
  - High-performance replay benchmark measured at ~1.6M events/sec.
  - Exported append-only JSONL evidence files (`fixtures/deliveries.jsonl`, `fixtures/decisions.jsonl`).
- **Phase 3:**
  - Versioned relational schema DDL (`warehouse/schema.sql`).
  - Bounded Snowflake staging, loading, and auto-suspending teardown scripts (`warehouse/load.sql`, `warehouse/teardown.sql`).
  - Analytical SQL queries for midpoints, spreads, and 11-sample sliding window volatilities (`warehouse/analytics.sql`).
  - Offline SQLite relational warehouse runner (`warehouse/local_warehouse.py`) providing 100% offline verification.
- **Phase 4:**
  - DepGraph temporal dependency registry (`depgraph/registry.py`) with cycle detection and topological ordering.
  - Impact analyzer (`depgraph/impact_analyzer.py`) verifying exact affected vs unaffected sets.
  - Verified honest recovery: snapshot resync restores current book while leaving older historical gaps incomplete.
  - Planned and executed minimal topological recomputation generating Revision 2 for affected historical windows.
- **Phase 5:**
  - Local HTTP REST dashboard server (`app/server.py`) with zero external cloud dependencies.
  - Interactive single-page UI (`app/index.html`, `app/style.css`, `app/app.js`) with 3 views: Run Overview, Incident Investigation, Recovery Comparison.
  - Keyboard navigation (`1`, `2`, `3`) and responsive dark terminal layout.
- **Phase 6 & 7:**
  - Documented Coinbase Exchange L2 protocol seam and resync policy in `docs/coinbase_adapter_seam.md`.
  - Comprehensive evaluation benchmark report in `docs/evaluation.md`.
  - Documented before-and-after incident case study in `README.md`.
- **Phase 8:**
  - GitHub Actions offline CI workflow (`.github/workflows/ci.yml`).
  - Architecture overview (`ARCHITECTURE.md`) and Architectural Decision Records (`DECISIONS.md`).
  - Full handover documentation with Second Mind review and Codex prompt (`HANDOVER.md`).
