# MarketTrace — Implementation Roadmap

This roadmap tracks the verified progression across project phases. Each phase requires an offline-verifiable gate and a Second Mind review before proceeding.

| Phase | Focus | Status | Key Deliverable & Gate |
|---|---|---|---|
| **Phase 0** | Audit & Foundation Scaffold | **IN PROGRESS** (Passed gate, pending review) | Toolchain verification, repo strategy, shared data contract, C++ and Python contract tests passing. |
| **Phase 1** | Offline Reference & Fixtures | Planned | Independent Python oracle, deterministic fixture generator (clean + faulted cases), hidden evaluator manifest. |
| **Phase 2** | C++ Engine & Replay | Planned | C++20 normalized parser, order book, deterministic replay, decision logging, bit-for-bit oracle parity. |
| **Phase 3** | Snowflake Experiment Warehouse | Planned | Versioned schema, bounded batch stage/load, historical SQL calculations (midpoint, spread, volatility). |
| **Phase 4** | DepGraph Impact & Repair | Planned | Typed temporal dependency registry, affected vs unaffected window tracking, topological recomputation plan. |
| **Phase 5** | Investigation Dashboard | Planned | 3 focused views (Run Overview, Incident Investigation, Recovery Comparison), credential-free local run. |
| **Phase 6** | Optional Live Adapter | Optional | Bounded Coinbase Exchange L2 capture with explicit gap handling. |
| **Phase 7** | Evaluation & Case Study | Planned | Benchmark measurements, reproducibility check, before/after case study in README. |
| **Phase 8** | Antigravity Handoff | Planned | End-to-end clean checkout test pass, complete documentation, packaging for Codex audit. |
| **Phase 9** | Codex Final Review | Planned | Independent verification, code/UX polish, publication to target repository. |
