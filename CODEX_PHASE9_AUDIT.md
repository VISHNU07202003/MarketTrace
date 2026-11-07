# Independent Phase 9 audit — 2026-11-06

## Scope and provenance

Reviewed the 72 source files from the supplied `MarketTrace_Codex_Handoff.zip` in an isolated workspace. The ZIP did not include `.git`, so the historical Antigravity SHA and branch cannot be proved. The local import baseline is `0132ca5` on `codex-review`, created for review only. The user's original DepGraph repository was not changed; this copy has no MarketTrace GitHub remote.

## Findings and resolution

| Finding in handoff | Review action | Current boundary |
|---|---|---|
| Snowflake runner printed preparation without actually connecting; SQL had gap-bridging and nested-window logic | Runner now explicitly fails when credentials are present; SQL analytics draft withdrawn with a cloud implementation gate | No Snowflake ingestion, SQL validation, cost measurement, or live account use |
| Warehouse checkpoints came directly from oracle expected data; old numerical comparison rechecked the same input | CLI can export actual engine checkpoints; runner compares them with reference before SQLite load; tests independently verify selected volatility windows by formula | SQLite still consumes replay checkpoints and is not independent proof of book reconstruction |
| Dashboard used hardcoded impacted rows and declared revision 2 without persisted recomputation | Added retained synthetic update and clean/damaged/repaired replay; API builds calculated branch comparisons, labels source, and leaves revision unset | Selective execution/persisted revisions pending |
| Snapshot reset marked an empty book VALID; malformed input could leave a book VALID | C++/Python now withhold validity until bid/ask restored, block incremental updates after an incomplete book, and reject crossed levels | Synthetic simplified book rules; no provider protocol validation |
| Midpoint integer division lost half ticks | Added exact bid+ask tick sum and calculates half-tick value downstream | Legacy floor `midpoint_ticks` retained for compatibility |
| 111-event microbenchmark, zero-ns measurements, 100% accuracy and Rev2 claims appeared in public docs | Removed benchmark from correctness test; replaced README/evaluation/status claims | No credible p50, throughput, real-world precision/recall, or superiority figure |
| Seeded holdout reused the same fault schedule | Described honestly; added a distinct focused retained-event incident | A truly structurally independent holdout remains pending |

## Reproduction in review workspace

Linux, GCC 13.3, Python 3.12; CMake installed into the local Python user bin. From repository root:

```sh
python3 -m pytest -q
/root/.local/bin/cmake -S . -B build
/root/.local/bin/cmake --build build -j 4
/root/.local/bin/ctest --test-dir build --output-on-failure
./build/markettrace_cli fixtures/incident_damaged.json --output runs/incident_damaged_engine.json
python3 -m warehouse.snowflake_runner
node --check app/app.js
```

Observed: **26 Python tests passed**, **2/2 CTest tests passed**, 104-event damaged C++ replay with final book VALID, **104 delivery/decision/checkpoint rows and 306 SQLite analytical rows**, with 59 valid/39 incomplete rolling-volatility update results. The C++ fixture agreement tests also covered 111 clean, 119 faulted, 119 seeded holdout, and 105/104/105 incident branch events. `node --check` parsed the dashboard script. An additional direct `g++ -DNDEBUG` build ran both C++ test binaries with source assertions explicitly re-enabled. No browser visual regression test was conducted.

The controlled comparison shows `inc_0060` missing, `inc_0061` incomplete, current book valid after the full second-80 snapshot, and historical windows valid again only in the separate repaired branch. The second-91 update window becomes valid in all branches after 11 regular samples.

## Open gates

1. Implement a real bounded Snowflake loader and run corrected SQL with an actual account; compare query output and measure credits. The draft `load.sql`, `schema.sql`, and `teardown.sql` are unverified designs, and `analytics.sql` contains no runnable cloud volatility query.
2. Persist immutable source identity, configuration and calculation versions, and verified revision-2 results; plan-only impact is not recomputation execution. Current SQLite evidence keys assume globally unique delivery IDs across runs.
3. Expand from simplified synthetic snapshots to provider-specific source sequence/reconnection semantics; add structurally different frozen holdout scenarios and adversarial hand-calculated cases.
4. Measure performance with an appropriate repeatable workload and distribution. The earlier 111-event timing cannot substantiate production latency or throughput.
5. Choose publication target and licensing/attribution, then compare this isolated import with the actual upstream Git history before pushing.
