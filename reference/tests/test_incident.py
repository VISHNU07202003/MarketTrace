"""Causal checks for the retained-event incident, beyond fixture-file equality."""

import json

from reference.incident import build_incident, MISSING_STEP, SNAPSHOT_STEP
from reference.models import QualityState
from reference.oracle import ReferenceOracle


def replay(events):
    oracle = ReferenceOracle()
    return {ev.delivery_id: oracle.apply(ev) for ev in events}


def test_missing_event_is_original_evidence_and_repair_is_a_separate_branch():
    clean, damaged, withheld = build_incident()
    assert withheld.delivery_id == "inc_0060"
    assert len(clean) == len(damaged) + 1
    assert [ev.delivery_id for ev in damaged] == [ev.delivery_id for ev in clean if ev != withheld]
    assert withheld.model_dump() == json.loads(open("fixtures/incident_withheld_event.json").read())
    assert clean[MISSING_STEP + 2].delivery_id == withheld.delivery_id


def test_snapshot_restores_current_only_after_both_sides():
    clean, damaged, _ = build_incident()
    complete = replay(clean)
    broken = replay(damaged)
    assert complete["inc_0061"][0].resulting_book_state == QualityState.VALID
    assert broken["inc_0061"][0].resulting_book_state == QualityState.INCOMPLETE
    assert broken["inc_0079"][1].midpoint_half_ticks is None
    assert broken["inc_resync_reset"][0].resulting_book_state == QualityState.INCOMPLETE
    assert broken["inc_resync_bid"][0].resulting_book_state == QualityState.INCOMPLETE
    assert broken["inc_resync_ask"][0].resulting_book_state == QualityState.VALID
    assert broken["inc_0081"][0].resulting_book_state == QualityState.VALID
    assert broken["inc_0091"][1].midpoint_half_ticks == complete["inc_0091"][1].midpoint_half_ticks


def test_half_tick_is_preserved_for_odd_bid_ask_sum():
    complete = replay(build_incident()[0])
    midpoint = complete["inc_0061"][1]
    assert midpoint.midpoint_half_ticks == 12_001_061
    assert midpoint.midpoint_ticks == 6_000_530
    assert midpoint.midpoint_half_ticks / 2 == 6_000_530.5
