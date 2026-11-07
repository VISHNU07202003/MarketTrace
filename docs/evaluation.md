# Evaluation: Phase 9 offline evidence

This evaluation describes the reviewed synthetic fixture, not a live feed or Snowflake account. Commands were run from the repository root in the Codex Linux workspace on 2026-11-06; see `CODEX_PHASE9_AUDIT.md` for build details.

| Check | Observed result | Boundary |
|---|---|---|
| Python tests | 26 passed | Reference, graph, SQLite, HTTP API |
| C++ tests | Contract and replay binaries passed with `-DNDEBUG`, assertions re-enabled by source | Direct `g++ -std=c++20 -O2` build; CMake unavailable in this workspace |
| C++ reference agreement | 111/111 clean, 119/119 faulted, 119/119 seeded holdout; focused 105/104/105 branches | Checked decisions and quote/midpoint fields; shared requirements can still be wrong |
| Damaged incident warehouse | 104 deliveries, 104 decisions, 104 checkpoints, 306 result rows | Local SQLite only; 59 VALID and 39 INCOMPLETE update-volatility rows |
| Cloud ingestion/SQL | Not run | SQL drafts have not been validated on Snowflake; no credits observed |
| Live market feed | Not run | Coinbase adapter seam only |
| Event latency/throughput | Not established | Original tiny 111-event timing and zero-nanosecond timer ticks were unsuitable for a public performance claim |

At `inc_0061`, the C++ branch reports a sequence gap, `INCOMPLETE` book, and null rolling volatility. The reset at second 80 remains incomplete until both snapshot sides arrive. The `inc_0091` volatility window is valid only after 11 consecutive one-second update samples. The repaired branch contains the original withheld `inc_0060` and recalculates earlier windows. This comparison is separate branch execution, not persisted revision 2 or a measured selective recomputation speedup.

The SQLite midpoint and spread calculation uses replay checkpoints. This is a useful contract check but not an independent proof of the engine's book math. Tests independently recompute selected 11-observation volatility values from the formula and compare within `1e-15` absolute tolerance. The holdout changes seed and values but repeats the same fault schedule. Do not interpret fixture agreement as real-world precision/recall or fault-detection guarantees.
