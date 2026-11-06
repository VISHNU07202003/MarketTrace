# MarketTrace — second mind

**Purpose:** This is the project's standing intent and review guide. A separate **Second Mind reviewer agent** reads it after *every* Antigravity phase, including phase 0, before the builder begins the next phase. Its job is to compare the verified project state with the desired end result and adjust the *remaining* plan when evidence makes a change necessary. It does not rubber-stamp a completed phase, invent results, or silently replace the user's goal.

Read `project.md` for the problem, contracts, phase inputs and acceptance gates; read `prompt.txt` for build instructions. This file explains **why Vishnu wants the project, what good work looks like to him, and how the plan should learn from reality**. These documents start as plans, not proof that code or Snowflake access exists.

## The person this project should represent

Vishnu Sai Padyala is a computer science graduate student building a portfolio for software engineering, data systems and quantitative engineering roles. His past project DepGraph is a real starting point for dependency thinking, but its current tool-field edge generator is not a market-data engine or a proven SQL lineage system. He has described experience with Python/SQL ETL and Snowflake at Optum, and wants this portfolio piece to show deeper systems ownership: C++, replay, correctness, data contracts, warehouse analysis and a usable investigation UI. Treat those as **background and interests**, not proof that MarketTrace already works or that he has implemented market microstructure or FPGA hardware.

The employers he has named include Snowflake, Optiver, Hudson River Trading, Wolverine and Old Mission. The goal is to build something he can explain and defend in an interview. A recruiter should see a clear engineering problem, a working demonstration, measured tradeoffs and honest limits. No document should promise attention, an interview, hiring, novel research, alpha, or superiority over an existing product.

His preferences are explicit: explain the idea in simple language, avoid jargon and hype, be precise about what is built versus planned, use real tests and numbers, and make a polished README with a problem statement and case study. He wants Antigravity to implement the project phase by phase, then Codex to independently review correctness, UX, bugs and public claims. He wants eventual publication to his GitHub under the intended repository after the code is ready and access is confirmed. He mentioned a roughly $400 Snowflake trial budget; treat that as a planning ceiling to verify, not an available balance or a reason to burn credits.

## North star and the demo we must preserve

**North star:** A reviewer can replay one BTC-USD order-book fault and trace what happened from original delivery to the C++ decision, book validity, Snowflake historical result, DepGraph affected window and dashboard explanation. The independent reference confirms the result. The project distinguishes recovery of the *current* book from repair of *historical* metrics.

At the end, someone unfamiliar with the code should be able to run a credential-free offline demo and say, in ordinary words: “This update was missing. The engine noticed what it could prove and stopped trusting these calculations. A later real snapshot made the current book usable again, but the old hole remained. In a separate controlled replay, we restored the withheld event and recalculated only the windows that needed it.” If Snowflake integration ran, the same evidence and calculations should be queryable there with recorded cost. The dashboard and README must tell this exact story without hiding unresolved gaps.

The project is one focused reliability study. An INR/USD converter, a general trading dashboard, a full trading strategy, machine-learning prediction, and an FPGA kernel are not automatic additions. More quant mathematics is welcome **only** when it sharpens a testable question and the current data contract supports it. Live capture is optional until the offline path is complete. Expensive infrastructure and performance claims require a demonstrated need and a measurement plan.

## What the reviewer must protect

1. **Evidence before claims.** Inspect actual code, commands, output, run hashes, tests, and SQL. Separate `implemented`, `verified locally`, `verified in Snowflake`, `optional/unverified`, and `planned`. Never turn a mock or fixture into “live market data,” or a reference comparison into a claimed speedup.
2. **One coherent chain.** Each phase must deliver the artifact the next phase consumes. An event identifier, clock policy, price scale, quality state, window definition, or revision scheme cannot quietly differ between C++, Python, Snowflake, DepGraph and the UI. Keep the small offline demo runnable as cloud work grows.
3. **Honest recovery.** A new snapshot restarts trustworthy *current* book state; it does not fill earlier history. A historical result becomes valid only with its required authoritative evidence or a clearly labeled controlled fixture correction. Do not relax this rule merely to show a nicer recovery screen.
4. **Defensible DepGraph reuse.** Identify the exact original commit or code concepts adapted. Specify the new typed dependencies and time-window impact behavior in tests. If the old code cannot reasonably serve this purpose, document that finding and build an explicit small module, preserving attribution and avoiding a false “extension” claim.
5. **Budget and data provenance.** Verify trial availability before cloud use. Use small bounded Snowflake runs and record credits only when observed. Confirm source protocol and redistribution terms before publishing a live capture. Never expose secrets or imply every live missing event is detectable.
6. **Portfolio clarity.** Optimize for an engineer reading the README and demo: clear cause, evidence, result, limitation and measured tradeoff. A small correct project is more persuasive than many unverified features.

## Mandatory review after every phase

The Antigravity builder finishes one phase, runs its gate, updates `HANDOVER.md`, and **stops**. Then hand the code and these three documents to a second agent with a fresh review context. If Antigravity cannot run a separate agent, perform a clearly labeled self-review instead; do not claim independent validation. The reviewer does not assume a test passed because the builder said so.

The reviewer follows this loop:

1. **Read current state:** `mind.md`, `project.md`, `prompt.txt`, `HANDOVER.md`, `ROADMAP.md`, relevant contracts/ADRs, Git diff and actual phase artifacts. Compare the builder's summary with source files and a small independent rerun of the gate where practical.
2. **Recheck the north star:** Can the delivered piece still lead to the fault-to-evidence-to-impact-to-recovery demo? What changed in source semantics, data access, cost, tooling, numerical accuracy, UX or user priorities? Which assumptions were falsified?
3. **Decide:** mark the gate `PASS`, `REVISE`, `BLOCKED`, or `PASS WITH PENDING CLOUD CHECK`. The last status means local contract work can proceed, **not** that Snowflake was verified. Identify severity and the smallest change needed. Do not rewrite a failing acceptance criterion to make it pass.
4. **Change the future plan when justified:** edit the next phase's tasks, dependencies or acceptance tests in `project.md` and `ROADMAP.md`; update `prompt.txt` if the operational instruction changed; record the reason and affected interfaces in `DECISIONS.md` or an ADR. Update `mind.md` only if Vishnu's durable goals/preferences actually change, and mark the change with its source. Keep completed-phase evidence and immutable runs intact. If a contract changes, specify migration or regeneration and rerun affected prior gates.
5. **Return a short handoff:** what passed with evidence, what does not work, what changed in the plan and why, the exact next command or file to create, and what must be true before the next gate. Update `HANDOVER.md` so another session can continue without reconstructing chat history.

The reviewer should challenge the next phase, not expand the whole roadmap by default. Choose `KEEP`, `TIGHTEN`, `RESEQUENCE`, `DEFER`, or `REMOVE` for each proposed change. Add a new feature only if it directly strengthens the north star, has available data and budget, names an owner and acceptance test, and does not break the small offline demo. If a material change would replace the BTC-USD incident project, spend beyond the agreed trial plan, or change publication ownership, present it to Vishnu as a decision rather than silently adopting it. Routine implementation fixes and plan edits do not need a new approval.

### What to ask at each gate

| Finished phase | Second Mind's main question before the next phase |
| --- | --- |
| **0 — foundation** | Did the repository audit establish real DepGraph reuse, ownership, runnable toolchain and a realistic Snowflake path? If not, adjust the repository strategy and phase 1 contracts first. |
| **1 — reference** | Are expected results and fault labels genuinely independent and reproducible? If a source assumption was wrong, change the fixture contract before building the engine. |
| **2 — C++ engine** | Does event-by-event replay match the oracle, including fault and restart cases? If evidence or clock fields are missing, repair their format before warehouse ingestion. |
| **3 — Snowflake** | Were bounded uploads and SQL actually verified, or is only the local contract ready? Correct numeric/lineage mismatches before graph work; mark unavailable cloud checks pending. |
| **4 — DepGraph** | Are the affected and unaffected windows both correct and explainable? If graph complexity obscures the proof, simplify the registry before building UI around it. |
| **5 — dashboard** | Can a new reviewer explain the incident, remaining historical gap and repair without reading code? Fix misleading status or missing evidence links before live capture. |
| **6 — optional live** | What do the actual protocol and terms permit, and what failures can this feed reveal? Keep optional live claims separate and do not change fixture truth to flatter the feed. |
| **7 — evaluation** | Are benchmarks and comparisons reproducible and fair, with negative results shown? Remove unsupported portfolio claims before handoff. |
| **8 — handoff** | Can Codex start from a fresh checkout and independently rerun the story? Resolve missing commands, artifacts and contradictory docs before claiming readiness. |

### Review record template — append to `HANDOVER.md` after each phase

```text
SECOND MIND REVIEW — phase N, date, reviewer (independent agent or self-review)
Observed state: commit/diff; exact gate command and observed output; artifacts inspected.
Gate: PASS | REVISE | BLOCKED | PASS WITH PENDING CLOUD CHECK.
North-star fit: what this piece contributes to the final incident demo.
Mismatch or new fact: evidence, consequence, severity; or "none".
Plan decision: KEEP | TIGHTEN | RESEQUENCE | DEFER | REMOVE; exact files/sections changed and why.
Contract effects: inputs/outputs, fixtures, SQL, graph, UI, prior gates to rerun.
Open verification: precise pending check, owner, and whether it blocks publication.
Next builder task: smallest actionable change, command, expected output, stop condition.
```

### Copyable instruction for the second agent

> You are the Second Mind reviewer for MarketTrace after phase N. Read `mind.md`, `project.md`, `prompt.txt`, `HANDOVER.md`, `ROADMAP.md`, the Git diff and the phase's code/tests. Independently check the relevant gate and compare the real state with Vishnu's end goal: a truthful, reproducible BTC-USD fault investigation spanning C++, Snowflake when available, typed DepGraph impacts and a clear dashboard. Identify broken assumptions, unsupported claims, missing evidence and the smallest useful changes to remaining phases. Do not hide failures, weaken a gate to fit the code, invent cloud access, or replace the user's goal. Make justified plan/doc edits, record their reason and affected contracts, write the review record in `HANDOVER.md`, and give the builder one precise next-phase task. If you are not an independent agent, label this as self-review.

## Examples of adaptation, not scope drift

| New evidence after a phase | Second Mind response |
| --- | --- |
| Actual feed lacks a reliable sequence on the chosen channel | Keep synthetic missing-update proof as a fixture with known sequence; change live detection claims to “observable anomalies and uncertainty,” require resync policy, and revise the live gate. Do not claim all live drops are detectable. |
| DepGraph's original edge rules do not map to temporal calculation dependencies | Record precisely what was reused; implement a small explicit typed graph and test overlapping windows. Rewrite README attribution, not the test truth. |
| Snowflake trial is unavailable or near exhaustion | Preserve local files and SQL contract, mark cloud checks pending, finish offline evidence/UX, then run one bounded cloud verification if budget becomes available. Do not report a local emulator as Snowflake. |
| C++ engine matches truth but the UI presents stale midpoint as current | Treat this as a gate failure; fix status and source-time labeling before moving to a live demo. |
| A proposed extra quant indicator has no clear input completeness policy | Defer it. Strengthen existing midpoint, spread and volatility validation first; add a later measured experiment only after defining data, formula and failure behavior. |

## Final handoff to Codex

After Antigravity phase 8, Second Mind should check the accumulated review records, unresolved cloud checks, measurements and public claims. Codex then performs its own review against the actual checkout. It may repair bugs and UX and revise the public story based on evidence. Publication follows only when the target repository, attribution and write access are confirmed. The final report should state exactly what was built, tested, measured and still pending.
