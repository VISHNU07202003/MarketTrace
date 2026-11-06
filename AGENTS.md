# MarketTrace — Agent Instructions & Operating Rules

## Project Mission & Identity
MarketTrace is an engineering portfolio project developed for Vishnu Sai Padyala targeting software engineering, data systems, and quantitative engineering roles.
It investigates one core reliability question: **When an incoming market-data stream is incomplete or corrupted, can we detect the issue, reconstruct a trustworthy state, and identify precisely which downstream analytics need correction?**

## Key Boundaries & Non-Goals
1. **Not a Trading Bot or HFT Engine**: Do not claim ultra-low latency, FPGA acceleration, or alpha generation.
2. **Evidence Before Claims**: Every claim must be backed by working, verifiable code and tests. Never treat mocks or fixtures as live market data.
3. **Honest Recovery**: A fresh authoritative snapshot restores the *current* book state; it does *not* magically heal historical gaps. Historical results are valid only if required historical evidence is provided.
4. **DepGraph Attribution**: Vishnu's prior project DepGraph (commit `b89b347`, Litmus assessment) inferenced tool-field dependencies from tool schemas. MarketTrace adapts the dependency concept for typed temporal market-data calculations (book -> quotes -> midpoint/spread -> log returns -> rolling volatility). Acknowledge DepGraph clearly and do not overwrite or modify the original assessment repo.
5. **Snowflake Budget Discipline**: Max trial budget ceiling is ~$400. Start offline-first; all core functionality must run without credentials or cloud dependencies. When Snowflake is used, use X-Small warehouse, auto-suspend, and teardown scripts. Never commit or log credentials.

## Phase Gates & Review
After every phase (0 through 8), the builder runs the gate tests, records verified commands and outputs in `HANDOVER.md`, and initiates a Second Mind review per `mind.md`. Only when the gate passes and the next task is agreed upon does work proceed to the next phase.
