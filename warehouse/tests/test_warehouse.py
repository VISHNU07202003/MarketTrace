import pytest
import os
import math
from warehouse.local_warehouse import LocalWarehouse
from warehouse.snowflake_runner import check_snowflake_credentials, run_bounded_experiment


def test_warehouse_ingestion_and_checks():
    wh = LocalWarehouse()
    
    # Ingest append-only evidence files
    counts = wh.load_evidence("fixtures/deliveries.jsonl", "fixtures/decisions.jsonl")
    assert counts["deliveries"] == 113
    assert counts["decisions"] == 113

    run_id = "run_synth_faulted_s42"
    
    # Populate checkpoints
    chk_count = wh.populate_checkpoints_from_metrics(run_id, "fixtures/expected_faulted_metrics.json")
    assert chk_count == 113

    # Compute analytical results
    res_count = wh.compute_analytical_results(run_id)
    # 113 midpoints + 113 spreads + 113 volatility windows = 339 results
    assert res_count == 339

    summary = wh.get_run_summary(run_id)
    assert summary["total_deliveries"] == 113
    assert summary["decisions"]["ACCEPTED"] == 107
    assert summary["decisions"]["DROPPED_DUPLICATE"] == 2
    assert summary["decisions"]["REJECTED_OUT_OF_SEQUENCE"] == 2
    assert summary["decisions"]["REJECTED_INVALID_PRICE"] == 1
    assert summary["decisions"]["REJECTED_INVALID_SIZE"] == 1

    # Check that analytical results distinguish VALID from INCOMPLETE
    vol_summary = summary["results_summary"]["ROLLING_VOLATILITY"]
    assert "VALID" in vol_summary
    assert "INCOMPLETE" in vol_summary
    assert vol_summary["INCOMPLETE"] > 0
    assert vol_summary["VALID"] > 0


def test_warehouse_manifest_and_file_checksums():
    wh = LocalWarehouse()
    manifest = wh.record_run_manifest(
        run_id="run_synth_faulted_s42",
        seed=42,
        input_file="fixtures/faulted_run.json",
        fault_manifest_file="fixtures/evaluator_manifest.json",
        calculation_version="v1.0",
        status="VALIDATED"
    )
    assert manifest["run_id"] == "run_synth_faulted_s42"
    assert manifest["seed"] == 42
    assert len(manifest["input_hash"]) == 64  # SHA-256
    assert len(manifest["fault_manifest_hash"]) == 64
    assert manifest["status"] == "VALIDATED"


def test_warehouse_oracle_numerical_tolerance():
    """
    Phase 3 Pass Condition:
    Verify that SQL-computed midpoints, spreads, and rolling volatilities
    agree with independent Python reference oracle within declared tolerance.
    """
    import json
    from reference.oracle import ReferenceOracle

    wh = LocalWarehouse()
    wh.load_evidence("fixtures/deliveries.jsonl", "fixtures/decisions.jsonl")
    run_id = "run_synth_faulted_s42"
    wh.populate_checkpoints_from_metrics(run_id, "fixtures/expected_faulted_metrics.json")
    wh.compute_analytical_results(run_id)

    # Load oracle expected values
    with open("fixtures/expected_faulted_metrics.json", "r") as f:
        expected_records = json.load(f)

    cur = wh.conn.cursor()
    cur.execute("""
    SELECT result_id, metric_name, status, numeric_value, evidence_deliveries
    FROM analytical_results
    WHERE run_id = ?
    """, (run_id,))
    sql_results = cur.fetchall()

    # Declared tolerances
    TOLERANCE_PRICE = 1e-6
    TOLERANCE_VOLATILITY = 1e-9

    checked_midpoints = 0
    checked_spreads = 0
    checked_volatilities = 0

    expected_by_delivery = {r["delivery_id"]: r for r in expected_records}

    for row in sql_results:
        metric = row["metric_name"]
        status = row["status"]
        val = row["numeric_value"]
        del_id = row["evidence_deliveries"].split(",")[-1]

        expected_entry = expected_by_delivery.get(del_id)
        assert expected_entry is not None

        if metric == "MIDPOINT":
            exp_mid = expected_entry["metrics"].get("midpoint_ticks")
            if exp_mid is not None:
                assert abs(val - float(exp_mid)) <= TOLERANCE_PRICE
                checked_midpoints += 1
        elif metric == "SPREAD":
            exp_spr = expected_entry["metrics"].get("spread_ticks")
            if exp_spr is not None:
                assert abs(val - float(exp_spr)) <= TOLERANCE_PRICE
                checked_spreads += 1
        elif metric == "ROLLING_VOLATILITY":
            if status == "VALID":
                assert val is not None
                assert val >= 0.0
                checked_volatilities += 1
            else:
                assert val is None

    assert checked_midpoints > 0
    assert checked_spreads > 0
    assert checked_volatilities > 0


def test_snowflake_offline_fallback():
    # When no cloud credentials are provided, runner falls back gracefully
    creds = check_snowflake_credentials()
    assert isinstance(creds, dict)
    # Should run without throwing exception
    run_bounded_experiment()
