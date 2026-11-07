"""Offline incident analytics contract; no Snowflake run is claimed here."""

import json
import math
import sqlite3

import pytest

from app.data import analytical_rows, load_branch
from reference.oracle import ReferenceOracle
from warehouse.local_warehouse import LocalWarehouse
from warehouse.snowflake_runner import run_bounded_experiment


def incident_warehouse(tmp_path, branch="damaged"):
    events, records, _ = load_branch(branch)
    deliveries = tmp_path / "deliveries.jsonl"
    decisions = tmp_path / "decisions.jsonl"
    replay = tmp_path / "replay.json"
    deliveries.write_text("".join(json.dumps(e) + "\n" for e in events))
    decisions.write_text("".join(json.dumps(r["decision"]) + "\n" for r in records))
    replay.write_text(json.dumps(records))
    warehouse = LocalWarehouse()
    counts = warehouse.load_evidence(str(deliveries), str(decisions))
    run_id = events[0]["run_id"]
    assert warehouse.populate_checkpoints_from_metrics(run_id, str(replay)) == len(events)
    return warehouse, run_id, counts, events, records, replay


def result(warehouse, delivery_id, metric):
    row = warehouse.conn.execute(
        "SELECT * FROM analytical_results WHERE result_id = ?",
        (f"res_{metric}_{delivery_id}",),
    ).fetchone()
    return dict(row) if row else None


def test_gap_stays_incomplete_until_real_snapshot_and_new_window(tmp_path):
    wh, run_id, counts, events, records, _ = incident_warehouse(tmp_path)
    assert counts == {"deliveries": 104, "decisions": 104}
    assert wh.compute_analytical_results(run_id) == 306
    assert result(wh, "inc_0059", "vol")["status"] == "VALID"
    assert result(wh, "inc_0060", "vol") is None
    assert result(wh, "inc_0061", "vol")["status"] == "INCOMPLETE"
    assert result(wh, "inc_0079", "vol")["numeric_value"] is None
    assert next(r for r in records if r["delivery_id"] == "inc_resync_ask")["decision"]["resulting_book_state"] == "VALID"
    assert result(wh, "inc_0081", "vol")["status"] == "INCOMPLETE"
    assert result(wh, "inc_0090", "vol")["status"] == "INCOMPLETE"
    assert result(wh, "inc_0091", "vol")["status"] == "VALID"
    assert result(wh, "inc_0091", "vol")["numeric_value"] is not None
    with pytest.raises(sqlite3.IntegrityError):
        wh.compute_analytical_results(run_id)


def test_analytics_match_independent_formula_on_sample_window(tmp_path):
    wh, run_id, _, events, records, _ = incident_warehouse(tmp_path, "clean")
    wh.compute_analytical_results(run_id)
    by_id = {r["delivery_id"]: r for r in records}
    for delivery_id in ("inc_0059", "inc_0061", "inc_0091"):
        end = int(delivery_id.split("_")[1])
        samples = [by_id[f"inc_{n:04d}"]["metrics"]["midpoint_half_ticks"] / 2
                   for n in range(end - 10, end + 1)]
        expected = ReferenceOracle.calculate_rolling_volatility(samples)
        row = result(wh, delivery_id, "vol")
        assert row["status"] == "VALID"
        assert math.isclose(row["numeric_value"], expected, abs_tol=1e-15)
        assert math.isclose(result(wh, delivery_id, "mid")["numeric_value"], samples[-1], abs_tol=0)
    # An odd tick sum retains the half tick instead of integer truncation.
    assert result(wh, "inc_0061", "mid")["numeric_value"] % 1 == .5
    assert analytical_rows("damaged")[0][("ROLLING_VOLATILITY", "inc_0061")]["status"] == "INCOMPLETE"


def test_manifest_is_immutable(tmp_path):
    wh = LocalWarehouse()
    path = tmp_path / "input.json"
    path.write_text("[]")
    manifest = wh.record_run_manifest("fixed", 303, str(path))
    assert len(manifest["input_hash"]) == 64
    with pytest.raises(sqlite3.IntegrityError):
        wh.record_run_manifest("fixed", 303, str(path))


def test_checkpoint_decisions_must_match_loaded_evidence(tmp_path):
    wh, run_id, _, _, records, replay = incident_warehouse(tmp_path)
    # Existing checkpoint IDs are immutable.
    with pytest.raises(sqlite3.IntegrityError):
        wh.populate_checkpoints_from_metrics(run_id, str(replay))
    wh2 = LocalWarehouse()
    deliveries = tmp_path / "deliveries.jsonl"
    decisions = tmp_path / "decisions.jsonl"
    wh2.load_evidence(str(deliveries), str(decisions))
    records[0]["decision"]["code"] = "REJECTED_INVALID_PRICE"
    replay.write_text(json.dumps(records))
    with pytest.raises(ValueError, match="does not match"):
        wh2.populate_checkpoints_from_metrics(run_id, str(replay))


def test_cloud_credentials_never_trigger_fake_success(monkeypatch):
    for key in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"):
        monkeypatch.setenv(key, "test-only")
    with pytest.raises(NotImplementedError, match="not implemented"):
        run_bounded_experiment()
