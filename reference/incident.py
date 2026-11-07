"""A focused, reproducible one-second incident with a genuinely retained event.

The faulted branch omits one synthetic event. The repaired branch inserts that
same event into the original ordering; neither branch is live market data.
"""

import hashlib
import json
from pathlib import Path

from reference.models import EventEnvelope, MessageKind, Side
from reference.oracle import ReferenceOracle


BASE_TIME_NS = 1_700_100_000_000_000_000
MISSING_STEP = 60
SNAPSHOT_STEP = 80
CADENCE_NS = 1_000_000_000


def _event(delivery_id: str, kind: MessageKind, side: Side, price: int,
           size: int, sequence: int, time_ns: int) -> EventEnvelope:
    return EventEnvelope(
        run_id="run_incident_clean_s303", delivery_id=delivery_id,
        source="synthetic_fixture", source_session="incident_session_01",
        instrument="BTC-USD", message_kind=kind,
        provider_sequence=sequence, provider_time_ns=time_ns,
        receive_time_ns=time_ns, replay_time_ns=time_ns,
        side=side, price_ticks=price, size_units=size,
        payload_hash=hashlib.sha256(delivery_id.encode()).hexdigest()[:16],
    )


def build_incident():
    events = [
        _event("inc_reset_0", MessageKind.SNAPSHOT, Side.NONE, 0, 0, 100, BASE_TIME_NS),
        _event("inc_bid_0", MessageKind.SNAPSHOT, Side.BID, 6_000_000, 100_000_000, 100, BASE_TIME_NS + 1),
        _event("inc_ask_0", MessageKind.SNAPSHOT, Side.ASK, 6_001_000, 100_000_000, 100, BASE_TIME_NS + 2),
    ]
    for step in range(1, 101):
        ts = BASE_TIME_NS + step * CADENCE_NS
        if step == SNAPSHOT_STEP:
            events.extend((
                _event("inc_resync_reset", MessageKind.SNAPSHOT, Side.NONE, 0, 0, 100 + step, ts - 3),
                _event("inc_resync_bid", MessageKind.SNAPSHOT, Side.BID, 6_000_000 + step,
                       100_000_000, 100 + step, ts - 2),
                _event("inc_resync_ask", MessageKind.SNAPSHOT, Side.ASK, 6_001_000,
                       100_000_000, 100 + step, ts - 1),
            ))
            # The snapshot represents step 80. Do not introduce a second event
            # at the same sample time or a duplicate provider sequence.
            continue
        events.append(_event(
            f"inc_{step:04d}", MessageKind.UPDATE, Side.BID,
            6_000_000 + step, 100_000_000, 100 + step, ts,
        ))

    missing = next(e for e in events if e.delivery_id == f"inc_{MISSING_STEP:04d}")
    damaged = [e for e in events if e.delivery_id != missing.delivery_id]
    return events, damaged, missing


def save_incident_fixtures(directory: str = "fixtures"):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    clean, damaged, missing = build_incident()
    for label, events in (("clean", clean), ("damaged", damaged), ("repaired", clean)):
        run_id = f"run_incident_{label}_s303"
        branch = [ev.model_copy(update={"run_id": run_id}) for ev in events]
        (path / f"incident_{label}.json").write_text(
            json.dumps([ev.model_dump() for ev in branch], indent=2) + "\n"
        )
        oracle = ReferenceOracle()
        results = []
        for ev in branch:
            dec, metrics = oracle.apply(ev)
            results.append({
                "delivery_id": ev.delivery_id,
                "decision": dec.model_dump(), "metrics": metrics.model_dump(),
            })
        (path / f"expected_incident_{label}_metrics.json").write_text(
            json.dumps(results, indent=2) + "\n"
        )
    (path / "incident_withheld_event.json").write_text(
        json.dumps(missing.model_dump(), indent=2) + "\n"
    )


if __name__ == "__main__":
    save_incident_fixtures()
