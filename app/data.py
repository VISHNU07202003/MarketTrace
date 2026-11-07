"""Read one recorded synthetic branch and calculate local historical results."""

import json
import tempfile
from pathlib import Path

from warehouse.local_warehouse import LocalWarehouse


ROOT = Path(__file__).resolve().parent.parent
BRANCHES = {"clean", "damaged", "repaired"}


def load_branch(branch: str):
    if branch not in BRANCHES:
        raise ValueError(f"Unknown run branch: {branch}")
    events = json.loads((ROOT / f"fixtures/incident_{branch}.json").read_text())
    engine_path = ROOT / f"runs/incident_{branch}_engine.json"
    reference = ROOT / f"fixtures/expected_incident_{branch}_metrics.json"
    records = json.loads((engine_path if engine_path.exists() else reference).read_text())
    if [ev["delivery_id"] for ev in events] != [r["delivery_id"] for r in records]:
        raise ValueError("Recorded engine run does not match fixture input")
    if engine_path.exists():
        expected = json.loads(reference.read_text())
        keys = ("best_bid_ticks", "best_ask_ticks", "midpoint_half_ticks", "spread_ticks")
        if len(records) != len(expected) or any(
            rec["decision"]["code"] != exp["decision"]["code"] or
            rec["decision"]["resulting_book_state"] != exp["decision"]["resulting_book_state"] or
            any(rec["metrics"].get(key) != exp["metrics"].get(key) for key in keys)
            for rec, exp in zip(records, expected)
        ):
            raise ValueError("Recorded engine run is stale or differs from reference; replay fixture again")
    return events, records, "C++ ENGINE" if engine_path.exists() else "PYTHON REFERENCE"


def analytical_rows(branch: str):
    events, records, source = load_branch(branch)
    with tempfile.TemporaryDirectory() as tmp:
        deliveries = Path(tmp) / "deliveries.jsonl"
        decisions = Path(tmp) / "decisions.jsonl"
        replay = Path(tmp) / "records.json"
        deliveries.write_text("".join(json.dumps(ev) + "\n" for ev in events))
        decisions.write_text("".join(json.dumps(r["decision"]) + "\n" for r in records))
        replay.write_text(json.dumps(records))
        wh = LocalWarehouse()
        wh.load_evidence(str(deliveries), str(decisions))
        wh.populate_checkpoints_from_metrics(events[0]["run_id"], str(replay))
        wh.compute_analytical_results(events[0]["run_id"])
        rows = wh.conn.execute("""SELECT metric_name, status, numeric_value,
            window_start_ns, window_end_ns, evidence_deliveries
            FROM analytical_results WHERE run_id = ?""", (events[0]["run_id"],)).fetchall()
    return {(r["metric_name"], r["evidence_deliveries"].split(",")[-1]): dict(r) for r in rows}, source
