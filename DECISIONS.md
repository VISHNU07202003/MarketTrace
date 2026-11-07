# Decisions and qualifications

1. **Synthetic first.** A retained update is deliberately omitted in one incident branch and restored in another. This permits a reproducible causal demonstration without claiming live-feed ground truth.
2. **Integer ticks and exact midpoint.** Prices are integer cents in the fixture. Store the sum of bid and ask ticks as `midpoint_half_ticks`, then divide by two for exact half-tick output; legacy integer `midpoint_ticks` remains for compatibility.
3. **Incomplete means stop incrementals.** A sequence gap, malformed price/size, crossed update, or incomplete snapshot cannot silently leave the book valid. A complete snapshot is needed to resume. Real exchange-specific snapshot sequencing needs separate validation.
4. **Explicit sample windows.** Volatility uses 11 one-second update samples, 10 log returns and sample standard deviation; invalid or irregular windows remain null. Snapshot/timer records do not add samples.
5. **Cloud gate stays closed.** SQLite is an offline contract implementation, not Snowflake. The old cloud runner printed success without executing SQL; it now fails fast when credentials are supplied. SQL remains a design draft.
6. **A plan is not a result.** DepGraph computes a topological plan without mutating node quality or revision. Separate fixture branch replay recalculates results; persisted revision 2 is pending.
