# Current architecture

A deterministic fixture feeds the C++20 replay engine and the independent Python implementation of the specified book rules. The C++ CLI can export decisions and checkpoint metrics. Local SQLite ingests delivery and decision evidence, checks their association, stores checkpoints, and calculates midpoint, spread, and 11-sample rolling volatility. A typed DepGraph models event and time-window dependencies. The dashboard shows branch records, local results, and a clean/damaged/repaired comparison.

There is no live Snowflake path in the runner. `warehouse/*.sql` are design drafts, not a validated cloud pipeline. A live exchange adapter is also absent. The dashboard uses Python fixture records unless it finds a matching C++ export in `runs/`; it checks that export against the fixture reference before showing it as C++ source.

Sequence gaps and malformed prices/sizes make the current book incomplete until a full reset and valid bid/ask snapshot. A snapshot affects current state; historical windows use their own sampled evidence. The graph's recomputation plan is read-only, while separate branch replay computes the comparison values. Durable revisions, exact minimal recomputation execution, cross-branch persisted lineage, and provider-specific snapshot protocol remain open engineering work.
