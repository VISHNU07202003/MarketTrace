# MarketTrace roadmap (reviewed 2026-11-06)

| Stage | State | Next gate |
|---|---|---|
| Deterministic oracle and fixtures | Offline verified | Add genuinely distinct fault schedule and adversarial hand-worked cases |
| C++ replay and state checks | Offline verified on synthetic inputs | Define real feed snapshot/sequence semantics before any adapter |
| SQLite historical metrics | Offline verified for incident contract | Add lineage/source hashes and independent SQL/book checks |
| DepGraph and dashboard | Local prototype | Persist verified recomputation revisions and benchmark selective work |
| Snowflake warehouse | **Not implemented/verified in cloud** | Build a bounded, credential-safe loader; validate SQL and credits on an actual account |
| Live feed | Not implemented | Verify exchange protocol and capture terms, then bounded capture |
| Performance evidence | Pending | Large-sample, separately measured CPU/IO/latency methodology |
| Publication | Pending | Choose GitHub destination and verify ownership, license, and attribution |

The original `project.md` is the phase blueprint; its acceptance gates are not proof that a phase passed.
