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
    assert summary["decisions"]["ACCEPTED"] == 106
    assert summary["decisions"]["REJECTED_OUT_OF_SEQUENCE"] == 2
    assert summary["decisions"]["DROPPED_DUPLICATE"] == 3
    assert summary["decisions"]["REJECTED_INVALID_PRICE"] == 1
    assert summary["decisions"]["REJECTED_INVALID_SIZE"] == 1

    # Check that analytical results distinguish VALID from INCOMPLETE
    vol_summary = summary["results_summary"]["ROLLING_VOLATILITY"]
    assert "VALID" in vol_summary
    assert "INCOMPLETE" in vol_summary
    assert vol_summary["INCOMPLETE"] > 0
    assert vol_summary["VALID"] > 0


def test_snowflake_offline_fallback():
    # When no cloud credentials are provided, runner falls back gracefully
    creds = check_snowflake_credentials()
    assert isinstance(creds, dict)
    # Should run without throwing exception
    run_bounded_experiment()
