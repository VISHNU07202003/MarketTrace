import pytest
from reference.models import (
    EventEnvelope,
    MessageKind,
    Side,
    DecisionCode,
    QualityState,
    ProcessingDecision,
    BookMetrics
)


def test_event_envelope_contract():
    envelope = EventEnvelope(
        run_id="run_001",
        delivery_id="del_001",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.BID,
        price_ticks=6000000,
        size_units=150000000,
        provider_sequence=101,
        receive_time_ns=1000000000
    )
    assert envelope.run_id == "run_001"
    assert envelope.instrument == "BTC-USD"
    assert envelope.side == Side.BID
    assert envelope.price_ticks == 6000000
    assert envelope.size_units == 150000000


def test_quality_state_and_decisions():
    decision = ProcessingDecision(
        delivery_id="del_002",
        code=DecisionCode.REJECTED_OUT_OF_SEQUENCE,
        reason="Sequence gap detected",
        decision_time_ns=1000005000,
        resulting_book_state=QualityState.INCOMPLETE
    )
    assert decision.code == DecisionCode.REJECTED_OUT_OF_SEQUENCE
    assert decision.resulting_book_state == QualityState.INCOMPLETE
