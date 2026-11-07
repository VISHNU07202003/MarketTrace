"""Offline warehouse experiment. Cloud execution is intentionally blocked.

The Snowflake SQL files remain unverified designs. This runner will never
silently fall back when credentials are present or claim an unexecuted load.
"""

import json
import os
import tempfile
from pathlib import Path

from warehouse.local_warehouse import LocalWarehouse


def check_snowflake_credentials() -> dict[str, str]:
    keys = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD")
    return {key: os.environ.get(key, "") for key in keys}


def run_bounded_experiment():
    if all(check_snowflake_credentials().values()):
        raise NotImplementedError(
            "Snowflake cloud loading is not implemented or verified; no cloud operation was attempted."
        )

    print("[STATUS] Offline SQLite experiment; Snowflake was not contacted.")
    events = json.loads(Path("fixtures/incident_damaged.json").read_text())
    engine_path = Path("runs/incident_damaged_engine.json")
    reference_path = Path("fixtures/expected_incident_damaged_metrics.json")
    records_path = engine_path if engine_path.exists() else reference_path
    records = json.loads(records_path.read_text())
    reference = json.loads(reference_path.read_text())

    if len(events) != len(records) or len(records) != len(reference):
        raise ValueError("Input and replay record counts differ")
    for event, record, expected in zip(events, records, reference):
        if event["delivery_id"] != record["delivery_id"] or record["delivery_id"] != expected["delivery_id"]:
            raise ValueError("Event/replay delivery IDs differ")
        for key in ("code", "resulting_book_state"):
            if record["decision"][key] != expected["decision"][key]:
                raise ValueError(f"Reference decision mismatch at {event['delivery_id']}")
        for key in ("best_bid_ticks", "best_ask_ticks", "midpoint_half_ticks", "spread_ticks"):
            if record["metrics"].get(key) != expected["metrics"].get(key):
                raise ValueError(f"Reference metric mismatch at {event['delivery_id']}: {key}")

    with tempfile.TemporaryDirectory() as temporary:
        deliveries = Path(temporary) / "deliveries.jsonl"
        decisions = Path(temporary) / "decisions.jsonl"
        deliveries.write_text("".join(json.dumps(event) + "\n" for event in events))
        decisions.write_text("".join(json.dumps(record["decision"]) + "\n" for record in records))
        warehouse = LocalWarehouse()
        counts = warehouse.load_evidence(str(deliveries), str(decisions))

    run_id = "run_incident_damaged_s303"
    warehouse.record_run_manifest(run_id, 303, "fixtures/incident_damaged.json")
    checkpoints = warehouse.populate_checkpoints_from_metrics(run_id, str(records_path))
    analytics = warehouse.compute_analytical_results(run_id)
    summary = warehouse.get_run_summary(run_id)
    print(f"[LOAD] {counts['deliveries']} deliveries, {counts['decisions']} decisions, "
          f"{checkpoints} checkpoints, {analytics} analytical result rows.")
    print(f"[SUMMARY] {summary['results_summary']}")
    print("[PASS] Checked C++ engine records against reference." if engine_path.exists()
          else "[REFERENCE ONLY] Run the C++ CLI with --output to verify the engine-to-warehouse chain.")
    return summary


if __name__ == "__main__":
    run_bounded_experiment()
