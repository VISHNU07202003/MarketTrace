"""
MarketTrace Deterministic Synthetic Fixture Generator.
Produces byte-identical BTC-USD order-book event traces and evaluator truth manifests.
"""

import random
import hashlib
import json
from typing import List, Dict, Any, Tuple
from reference.models import (
    EventEnvelope,
    MessageKind,
    Side,
    DecisionCode,
    QualityState
)
from reference.oracle import ReferenceOracle


class FixtureGenerator:
    def __init__(self, seed: int = 42, instrument: str = "BTC-USD"):
        self.seed = seed
        self.instrument = instrument

    def generate_trace(
        self,
        num_updates: int = 100,
        inject_faults: bool = False
    ) -> Tuple[List[EventEnvelope], List[Dict[str, Any]]]:
        """
        Generates an initial snapshot followed by `num_updates` updates.
        Returns:
            events: List of EventEnvelope
            evaluator_manifest: List of expected fault positions and annotations (hidden from engine)
        """
        rng = random.Random(self.seed)
        events: List[EventEnvelope] = []
        evaluator_manifest: List[Dict[str, Any]] = []

        run_id = f"run_synth_{'faulted' if inject_faults else 'clean'}_s{self.seed}"
        base_time_ns = 1_700_000_000_000_000_000  # Epoch ns anchor
        current_time_ns = base_time_ns
        provider_seq = 100
        delivery_counter = 1

        def next_delivery_id() -> str:
            nonlocal delivery_counter
            del_id = f"del_{delivery_counter:04d}"
            delivery_counter += 1
            return del_id

        # 1. Snapshot Reset
        snap_reset = EventEnvelope(
            run_id=run_id,
            delivery_id=next_delivery_id(),
            source="synthetic_fixture",
            source_session="synth_session_01",
            instrument=self.instrument,
            message_kind=MessageKind.SNAPSHOT,
            provider_sequence=provider_seq,
            receive_time_ns=current_time_ns,
            replay_time_ns=current_time_ns,
            side=Side.NONE,
            price_ticks=0,
            size_units=0,
            payload_hash=hashlib.sha256(b"snap_reset").hexdigest()[:16]
        )
        events.append(snap_reset)

        # 2. Initial Snapshot Book Levels (5 bids, 5 asks)
        base_bid = 6_000_000  # $60,000.00
        base_ask = 6_000_500  # $60,005.00
        tick_step = 100       # $1.00 step

        for i in range(5):
            current_time_ns += 1_000_000
            events.append(EventEnvelope(
                run_id=run_id,
                delivery_id=next_delivery_id(),
                source="synthetic_fixture",
                source_session="synth_session_01",
                instrument=self.instrument,
                message_kind=MessageKind.SNAPSHOT,
                provider_sequence=provider_seq,
                receive_time_ns=current_time_ns,
                replay_time_ns=current_time_ns,
                side=Side.BID,
                price_ticks=base_bid - (i * tick_step),
                size_units=rng.randint(50_000_000, 250_000_000),  # 0.5 to 2.5 BTC
                payload_hash=hashlib.sha256(f"bid_snap_{i}".encode()).hexdigest()[:16]
            ))
            events.append(EventEnvelope(
                run_id=run_id,
                delivery_id=next_delivery_id(),
                source="synthetic_fixture",
                source_session="synth_session_01",
                instrument=self.instrument,
                message_kind=MessageKind.SNAPSHOT,
                provider_sequence=provider_seq,
                receive_time_ns=current_time_ns,
                replay_time_ns=current_time_ns,
                side=Side.ASK,
                price_ticks=base_ask + (i * tick_step),
                size_units=rng.randint(50_000_000, 250_000_000),
                payload_hash=hashlib.sha256(f"ask_snap_{i}".encode()).hexdigest()[:16]
            ))

        # 3. Incremental Updates (100 updates)
        # Time step between events: 100ms
        for step in range(1, num_updates + 1):
            current_time_ns += 100_000_000  # 100ms

            # Determine if this step is an injected fault
            fault_type = None
            if inject_faults:
                if step == 20:
                    fault_type = "DUPLICATE_SEQUENCE"
                elif step == 28:
                    fault_type = "REORDERED_ARRIVAL"
                elif step == 35:
                    fault_type = "INVALID_PRICE"
                elif step == 50:
                    fault_type = "INVALID_SIZE"
                elif step == 58:
                    fault_type = "SIMULATED_PAUSE"
                elif step == 65:
                    fault_type = "SEQUENCE_GAP"
                elif step == 72:
                    fault_type = "GRACEFUL_RESTART"
                elif step == 80:
                    fault_type = "RESYNC_SNAPSHOT"

            side = Side.BID if rng.random() < 0.5 else Side.ASK
            price_offset = rng.randint(-3, 3) * tick_step
            price = (base_bid + price_offset) if side == Side.BID else (base_ask + price_offset)
            size = rng.randint(0, 300_000_000)  # 0 indicates level removal

            del_id = next_delivery_id()
            msg_kind = MessageKind.UPDATE
            session_id = "synth_session_01"

            if fault_type == "DUPLICATE_SEQUENCE":
                curr_seq = provider_seq  # Duplicate of the last sent sequence
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.DROPPED_DUPLICATE.value,
                    "expected_book_state": QualityState.VALID.value,
                    "comment": "Duplicate sequence number delivered; should be safely dropped"
                })

            elif fault_type == "REORDERED_ARRIVAL":
                curr_seq = provider_seq - 1  # Reordered earlier sequence
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.DROPPED_DUPLICATE.value,
                    "expected_book_state": QualityState.VALID.value,
                    "comment": "Reordered arrival delivered after higher sequence was processed; rejected as stale"
                })

            elif fault_type == "INVALID_PRICE":
                provider_seq += 1
                curr_seq = provider_seq
                price = -50_000  # Negative price
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.REJECTED_INVALID_PRICE.value,
                    "expected_book_state": QualityState.VALID.value,
                    "comment": "Nonpositive price ticks; should reject update"
                })

            elif fault_type == "INVALID_SIZE":
                provider_seq += 1
                curr_seq = provider_seq
                size = -10_000_000  # Negative size
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.REJECTED_INVALID_SIZE.value,
                    "expected_book_state": QualityState.VALID.value,
                    "comment": "Negative size units; should reject update"
                })

            elif fault_type == "SIMULATED_PAUSE":
                current_time_ns += 6_000_000_000
                msg_kind = MessageKind.TIMER
                side = Side.NONE
                price = 0
                size = 0
                curr_seq = None
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.ACCEPTED.value,
                    "expected_book_state": QualityState.STALE.value,
                    "comment": "Simulated pause triggers staleness heartbeat check; transitions book to STALE"
                })

            elif fault_type == "SEQUENCE_GAP":
                provider_seq += 2  # Skip one sequence number (simulate missing update)
                curr_seq = provider_seq
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.REJECTED_OUT_OF_SEQUENCE.value,
                    "expected_book_state": QualityState.INCOMPLETE.value,
                    "comment": "Observable sequence gap; marks order book state as INCOMPLETE"
                })

            elif fault_type == "GRACEFUL_RESTART":
                session_id = "synth_session_02"
                provider_seq += 5  # Restart sequence discontinuity
                curr_seq = provider_seq
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.REJECTED_OUT_OF_SEQUENCE.value,
                    "expected_book_state": QualityState.INCOMPLETE.value,
                    "comment": "Session restart discontinuity; remains INCOMPLETE until authoritative resync"
                })

            elif fault_type == "RESYNC_SNAPSHOT":
                provider_seq += 10
                curr_seq = provider_seq
                msg_kind = MessageKind.SNAPSHOT
                side = Side.NONE
                price = 0
                size = 0
                evaluator_manifest.append({
                    "delivery_id": del_id,
                    "step_index": step,
                    "fault_type": fault_type,
                    "expected_decision": DecisionCode.ACCEPTED.value,
                    "expected_book_state": QualityState.VALID.value,
                    "comment": "Authoritative resync snapshot; restores current book state to VALID"
                })

            else:
                provider_seq += 1
                curr_seq = provider_seq

            event = EventEnvelope(
                run_id=run_id,
                delivery_id=del_id,
                source="synthetic_fixture",
                source_session=session_id,
                instrument=self.instrument,
                message_kind=msg_kind,
                provider_sequence=curr_seq,
                receive_time_ns=current_time_ns,
                replay_time_ns=current_time_ns,
                side=side,
                price_ticks=price,
                size_units=size,
                payload_hash=hashlib.sha256(f"update_{step}_{del_id}".encode()).hexdigest()[:16]
            )
            events.append(event)

            # If resync snapshot, also inject fresh baseline quotes so book is populated immediately
            if fault_type == "RESYNC_SNAPSHOT":
                current_time_ns += 1_000_000
                events.append(EventEnvelope(
                    run_id=run_id,
                    delivery_id=next_delivery_id(),
                    source="synthetic_fixture",
                    source_session="synth_session_01",
                    instrument=self.instrument,
                    message_kind=MessageKind.SNAPSHOT,
                    provider_sequence=curr_seq,
                    receive_time_ns=current_time_ns,
                    replay_time_ns=current_time_ns,
                    side=Side.BID,
                    price_ticks=base_bid,
                    size_units=100_000_000,
                    payload_hash=hashlib.sha256(b"resync_bid").hexdigest()[:16]
                ))
                events.append(EventEnvelope(
                    run_id=run_id,
                    delivery_id=next_delivery_id(),
                    source="synthetic_fixture",
                    source_session="synth_session_01",
                    instrument=self.instrument,
                    message_kind=MessageKind.SNAPSHOT,
                    provider_sequence=curr_seq,
                    receive_time_ns=current_time_ns,
                    replay_time_ns=current_time_ns,
                    side=Side.ASK,
                    price_ticks=base_ask,
                    size_units=100_000_000,
                    payload_hash=hashlib.sha256(b"resync_ask").hexdigest()[:16]
                ))

        return events, evaluator_manifest


def build_and_save_fixtures(seed: int = 42, fixtures_dir: str = "fixtures"):
    import os
    os.makedirs(fixtures_dir, exist_ok=True)

    gen = FixtureGenerator(seed=seed)

    # 1. Clean run
    clean_events, _ = gen.generate_trace(num_updates=100, inject_faults=False)
    clean_path = os.path.join(fixtures_dir, "clean_run.json")
    with open(clean_path, "w") as f:
        json.dump([e.model_dump() for e in clean_events], f, indent=2)

    # Compute expected clean oracle metrics
    oracle_clean = ReferenceOracle()
    clean_metrics = []
    for ev in clean_events:
        dec, met = oracle_clean.apply(ev)
        clean_metrics.append({
            "delivery_id": ev.delivery_id,
            "decision": dec.model_dump(),
            "metrics": met.model_dump()
        })
    with open(os.path.join(fixtures_dir, "expected_clean_metrics.json"), "w") as f:
        json.dump(clean_metrics, f, indent=2)

    # 2. Faulted run
    faulted_events, manifest = gen.generate_trace(num_updates=100, inject_faults=True)
    faulted_path = os.path.join(fixtures_dir, "faulted_run.json")
    with open(faulted_path, "w") as f:
        json.dump([e.model_dump() for e in faulted_events], f, indent=2)

    # Save hidden evaluator manifest
    manifest_path = os.path.join(fixtures_dir, "evaluator_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Compute expected faulted oracle metrics
    oracle_faulted = ReferenceOracle()
    faulted_metrics = []
    for ev in faulted_events:
        dec, met = oracle_faulted.apply(ev)
        faulted_metrics.append({
            "delivery_id": ev.delivery_id,
            "decision": dec.model_dump(),
            "metrics": met.model_dump()
        })
    with open(os.path.join(fixtures_dir, "expected_faulted_metrics.json"), "w") as f:
        json.dump(faulted_metrics, f, indent=2)

    # Also generate frozen holdout dataset (seed 101) per Phase 7 requirements
    build_and_save_holdout_fixtures(seed=101, fixtures_dir=fixtures_dir)


def build_and_save_holdout_fixtures(seed: int = 101, fixtures_dir: str = "fixtures"):
    import os
    os.makedirs(fixtures_dir, exist_ok=True)
    gen = FixtureGenerator(seed=seed)

    # Clean holdout
    clean_events, _ = gen.generate_trace(num_updates=100, inject_faults=False)
    with open(os.path.join(fixtures_dir, "holdout_clean_run.json"), "w") as f:
        json.dump([e.model_dump() for e in clean_events], f, indent=2)

    oracle_clean = ReferenceOracle()
    clean_metrics = []
    for ev in clean_events:
        dec, met = oracle_clean.apply(ev)
        clean_metrics.append({
            "delivery_id": ev.delivery_id,
            "decision": dec.model_dump(),
            "metrics": met.model_dump()
        })
    with open(os.path.join(fixtures_dir, "expected_holdout_clean_metrics.json"), "w") as f:
        json.dump(clean_metrics, f, indent=2)

    # Faulted holdout
    faulted_events, manifest = gen.generate_trace(num_updates=100, inject_faults=True)
    with open(os.path.join(fixtures_dir, "holdout_faulted_run.json"), "w") as f:
        json.dump([e.model_dump() for e in faulted_events], f, indent=2)

    with open(os.path.join(fixtures_dir, "holdout_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    oracle_faulted = ReferenceOracle()
    faulted_metrics = []
    for ev in faulted_events:
        dec, met = oracle_faulted.apply(ev)
        faulted_metrics.append({
            "delivery_id": ev.delivery_id,
            "decision": dec.model_dump(),
            "metrics": met.model_dump()
        })
    with open(os.path.join(fixtures_dir, "expected_holdout_faulted_metrics.json"), "w") as f:
        json.dump(faulted_metrics, f, indent=2)

    print(f"Successfully generated frozen holdout fixtures with seed {seed}:")
    print(f"  - fixtures/holdout_clean_run.json ({len(clean_events)} events)")
    print(f"  - fixtures/holdout_faulted_run.json ({len(faulted_events)} events)")


if __name__ == "__main__":
    build_and_save_fixtures()
