import json
import pytest
from reference.generator import FixtureGenerator
from reference.models import DecisionCode, QualityState


def test_generator_determinism():
    """Verify that same seed produces byte-identical serialized JSON events."""
    gen1 = FixtureGenerator(seed=123)
    events1_clean, _ = gen1.generate_trace(num_updates=50, inject_faults=False)
    events1_faulted, manifest1 = gen1.generate_trace(num_updates=50, inject_faults=True)

    gen2 = FixtureGenerator(seed=123)
    events2_clean, _ = gen2.generate_trace(num_updates=50, inject_faults=False)
    events2_faulted, manifest2 = gen2.generate_trace(num_updates=50, inject_faults=True)

    json1_clean = json.dumps([e.model_dump() for e in events1_clean], sort_keys=True)
    json2_clean = json.dumps([e.model_dump() for e in events2_clean], sort_keys=True)
    assert json1_clean == json2_clean

    json1_faulted = json.dumps([e.model_dump() for e in events1_faulted], sort_keys=True)
    json2_faulted = json.dumps([e.model_dump() for e in events2_faulted], sort_keys=True)
    assert json1_faulted == json2_faulted

    assert json.dumps(manifest1, sort_keys=True) == json.dumps(manifest2, sort_keys=True)


def test_evaluator_manifest_isolation_and_coverage():
    """Verify that the evaluator manifest correctly annotates all 5 planned injected faults."""
    gen = FixtureGenerator(seed=42)
    _, manifest = gen.generate_trace(num_updates=100, inject_faults=True)

    fault_types = [m["fault_type"] for m in manifest]
    assert fault_types == [
        "DUPLICATE_SEQUENCE",
        "INVALID_PRICE",
        "INVALID_SIZE",
        "SEQUENCE_GAP",
        "RESYNC_SNAPSHOT"
    ]

    expected_decisions = [m["expected_decision"] for m in manifest]
    assert expected_decisions == [
        DecisionCode.DROPPED_DUPLICATE.value,
        DecisionCode.REJECTED_INVALID_PRICE.value,
        DecisionCode.REJECTED_INVALID_SIZE.value,
        DecisionCode.REJECTED_OUT_OF_SEQUENCE.value,
        DecisionCode.ACCEPTED.value
    ]

    expected_states = [m["expected_book_state"] for m in manifest]
    assert expected_states == [
        QualityState.VALID.value,
        QualityState.VALID.value,
        QualityState.VALID.value,
        QualityState.INCOMPLETE.value,
        QualityState.VALID.value
    ]
