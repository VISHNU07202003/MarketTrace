"""
MarketTrace Holdout Dataset Evaluation Test.
Tests independent execution against the frozen held-out fixture family (seed 101).
Verifies that detection rules and oracle calculations generalize without tuning bias.
"""

import json
import pytest
from reference.models import EventEnvelope, DecisionCode, QualityState
from reference.oracle import ReferenceOracle


def test_holdout_clean_replay_evaluation():
    oracle = ReferenceOracle(instrument="BTC-USD")
    with open("fixtures/holdout_clean_run.json", "r") as f:
        events = [EventEnvelope(**e) for e in json.load(f)]
    with open("fixtures/expected_holdout_clean_metrics.json", "r") as f:
        expected = json.load(f)

    assert len(events) == len(expected)
    for ev, exp in zip(events, expected):
        dec, met = oracle.apply(ev)
        assert dec.code.value == exp["decision"]["code"]
        assert dec.resulting_book_state.value == exp["decision"]["resulting_book_state"]
        assert met.best_bid_ticks == exp["metrics"]["best_bid_ticks"]
        assert met.best_ask_ticks == exp["metrics"]["best_ask_ticks"]
        assert met.midpoint_ticks == exp["metrics"]["midpoint_ticks"]
        assert met.spread_ticks == exp["metrics"]["spread_ticks"]


def test_holdout_faulted_replay_evaluation():
    oracle = ReferenceOracle(instrument="BTC-USD")
    with open("fixtures/holdout_faulted_run.json", "r") as f:
        events = [EventEnvelope(**e) for e in json.load(f)]
    with open("fixtures/expected_holdout_faulted_metrics.json", "r") as f:
        expected = json.load(f)
    with open("fixtures/holdout_manifest.json", "r") as f:
        manifest = json.load(f)

    assert len(events) == len(expected)
    assert len(manifest) == 8

    # Verify that all 8 holdout injected faults are detected exactly as expected
    detected_faults = 0
    for ev, exp in zip(events, expected):
        dec, met = oracle.apply(ev)
        assert dec.code.value == exp["decision"]["code"]
        assert dec.resulting_book_state.value == exp["decision"]["resulting_book_state"]

        # Check against manifest
        matching_fault = next((m for m in manifest if m["delivery_id"] == ev.delivery_id), None)
        if matching_fault:
            assert dec.code.value == matching_fault["expected_decision"]
            assert dec.resulting_book_state.value == matching_fault["expected_book_state"]
            detected_faults += 1

    assert detected_faults == 8
