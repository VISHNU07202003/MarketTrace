# MarketTrace — Implementation Roadmap

This roadmap tracks the verified progression across project phases. Each phase requires an offline-verifiable gate and a Second Mind review before proceeding.

| Phase | Focus | Status | Key Deliverable & Gate |
|---|---|---|---|
| **Phase 0** | Audit & Foundation Scaffold | **COMPLETE (PASS)** | Toolchain verification, repo strategy, shared data contract, C++ and Python contract tests passing. |
| **Phase 1** | Offline Reference & Fixtures | **COMPLETE (PASS)** | Independent Python oracle, deterministic fixture generator (clean + faulted cases), hidden evaluator manifest, 7/7 pytest tests passing. |
| **Phase 2** | C++ Engine & Replay | **COMPLETE (PASS)** | C++20 normalized parser, order book, deterministic replay from JSON fixture, decision logging, 100% bit-for-bit oracle parity, ~1.6M events/sec. |
| **Phase 3** | Snowflake Experiment Warehouse | **COMPLETE (PASS WITH PENDING CLOUD CHECK)** | Versioned schema (DDL), staged batch loaders, SQL historical metrics (midpoint, spread, volatility), local SQLite emulator passing 100% offline. Live cloud check pending credentials. |
| **Phase 4** | DepGraph Impact & Repair | **COMPLETE (PASS)** | Typed temporal dependency registry, affected vs unaffected window tracking, topological recomputation plan, honest recovery verification. |
| **Phase 5** | Investigation Dashboard | **COMPLETE (PASS)** | 3 focused views (Run Overview, Incident Investigation, Recovery Comparison), keyboard and responsive navigation, credential-free local web server (5/5 tests passing). |
| **Phase 6** | Optional Live Adapter | **COMPLETE (SEAM DOCUMENTED)** | Bounded Coinbase Exchange L2 capture seam documented with explicit unknown-gap handling in `docs/coinbase_adapter_seam.md`. |
| **Phase 7** | Evaluation & Case Study | **COMPLETE (PASS)** | Benchmark measurements (~1.6M events/sec, <100ns p50), before/after case study in `README.md`, full evaluation report in `docs/evaluation.md`. |
| **Phase 8** | Antigravity Handoff | **COMPLETE (PASS)** | End-to-end clean checkout test pass (19/19 passing), complete documentation (ARCHITECTURE, DECISIONS, CHANGELOG, CI), packaging for Codex audit. |
| **Phase 9** | Codex Final Review | **READY TO PROCEED** | Independent verification, code/UX polish, publication to target repository. |
