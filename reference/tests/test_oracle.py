import math
import pytest
from reference.models import (
    EventEnvelope,
    MessageKind,
    Side,
    DecisionCode,
    QualityState
)
from reference.oracle import ReferenceOracle


def test_oracle_order_book_operations():
    oracle = ReferenceOracle(instrument="BTC-USD")
    assert oracle.state == QualityState.VALID

    # 1. Reset snapshot
    snap_reset = EventEnvelope(
        run_id="test_run",
        delivery_id="d1",
        instrument="BTC-USD",
        message_kind=MessageKind.SNAPSHOT,
        side=Side.NONE,
        price_ticks=0,
        size_units=0,
        provider_sequence=10
    )
    dec, m = oracle.apply(snap_reset)
    assert dec.code == DecisionCode.ACCEPTED
    assert m.is_empty is True

    # 2. Add bid and ask levels
    bid_event = EventEnvelope(
        run_id="test_run",
        delivery_id="d2",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.BID,
        price_ticks=5_000_000,   # $50,000.00
        size_units=100_000_000,  # 1.0 BTC
        provider_sequence=11
    )
    dec, m = oracle.apply(bid_event)
    assert dec.code == DecisionCode.ACCEPTED
    assert m.best_bid_ticks == 5_000_000

    ask_event = EventEnvelope(
        run_id="test_run",
        delivery_id="d3",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.ASK,
        price_ticks=5_001_000,   # $50,010.00
        size_units=200_000_000,  # 2.0 BTC
        provider_sequence=12
    )
    dec, m = oracle.apply(ask_event)
    assert dec.code == DecisionCode.ACCEPTED
    assert m.best_bid_ticks == 5_000_000
    assert m.best_ask_ticks == 5_001_000
    assert m.spread_ticks == 1_000
    assert m.midpoint_ticks == 5_000_500
    assert m.is_crossed is False
    assert m.is_empty is False

    # 3. Level deletion when size is 0
    delete_ask = EventEnvelope(
        run_id="test_run",
        delivery_id="d4",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.ASK,
        price_ticks=5_001_000,
        size_units=0,            # 0 size removes price level
        provider_sequence=13
    )
    dec, m = oracle.apply(delete_ask)
    assert dec.code == DecisionCode.ACCEPTED
    assert m.best_ask_ticks is None
    assert m.is_empty is True


def test_oracle_sequence_gap_and_resync():
    oracle = ReferenceOracle(instrument="BTC-USD")

    # Sequence 100
    e1 = EventEnvelope(
        run_id="r1",
        delivery_id="d1",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.BID,
        price_ticks=1000,
        size_units=10,
        provider_sequence=100
    )
    oracle.apply(e1)

    # Sequence gap: jump to 105
    e2 = EventEnvelope(
        run_id="r1",
        delivery_id="d2",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.BID,
        price_ticks=1010,
        size_units=10,
        provider_sequence=105
    )
    dec2, _ = oracle.apply(e2)
    assert dec2.code == DecisionCode.REJECTED_OUT_OF_SEQUENCE
    assert dec2.resulting_book_state == QualityState.INCOMPLETE
    assert oracle.state == QualityState.INCOMPLETE

    # Resync snapshot restores state to VALID
    resync = EventEnvelope(
        run_id="r1",
        delivery_id="d3",
        instrument="BTC-USD",
        message_kind=MessageKind.SNAPSHOT,
        side=Side.NONE,
        price_ticks=0,
        size_units=0,
        provider_sequence=200
    )
    dec3, _ = oracle.apply(resync)
    assert dec3.code == DecisionCode.ACCEPTED
    assert dec3.resulting_book_state == QualityState.VALID
    assert oracle.state == QualityState.VALID


def test_oracle_rolling_volatility_exact_math():
    """
    Hand-worked verification of 11 consecutive 1-second sample midpoints:
    r_i = ln(m_i / m_{i-1})
    Sample variance = sum((r_i - mean_r)^2) / 9
    Sample stddev = sqrt(variance)
    """
    midpoints = [
        100.0, 101.0, 102.0, 101.5, 103.0,
        102.5, 104.0, 103.5, 105.0, 104.5, 106.0
    ]
    assert len(midpoints) == 11

    # Hand computation:
    expected_returns = [math.log(midpoints[i] / midpoints[i - 1]) for i in range(1, 11)]
    expected_mean = sum(expected_returns) / 10.0
    expected_var = sum((r - expected_mean) ** 2 for r in expected_returns) / 9.0
    expected_vol = math.sqrt(expected_var)

    calculated_vol = ReferenceOracle.calculate_rolling_volatility(midpoints)
    assert calculated_vol is not None
    assert math.isclose(calculated_vol, expected_vol, rel_tol=1e-12)

    # Incomplete window returns None
    assert ReferenceOracle.calculate_rolling_volatility(midpoints[:10]) is None
    assert ReferenceOracle.calculate_rolling_volatility(midpoints + [107.0]) is None

    # Invalid price <= 0 returns None
    corrupt_midpoints = midpoints.copy()
    corrupt_midpoints[5] = -10.0
    assert ReferenceOracle.calculate_rolling_volatility(corrupt_midpoints) is None


def test_oracle_timer_staleness():
    oracle = ReferenceOracle(instrument="BTC-USD")
    
    # 1. Update at t = 1,000,000,000 ns
    e1 = EventEnvelope(
        run_id="r1",
        delivery_id="d1",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.BID,
        price_ticks=5_000_000,
        size_units=100_000_000,
        provider_sequence=1,
        receive_time_ns=1_000_000_000
    )
    oracle.apply(e1)
    assert oracle.state == QualityState.VALID

    # 2. Heartbeat at t = 2,000,000,000 ns (elapsed 1s <= 5s) -> stays VALID
    t1 = EventEnvelope(
        run_id="r1",
        delivery_id="d2",
        instrument="BTC-USD",
        message_kind=MessageKind.TIMER,
        receive_time_ns=2_000_000_000
    )
    dec_t1, _ = oracle.apply(t1)
    assert dec_t1.code == DecisionCode.ACCEPTED
    assert oracle.state == QualityState.VALID

    # 3. Heartbeat at t = 8,000,000,000 ns (elapsed 7s > 5s) -> transitions to STALE!
    t2 = EventEnvelope(
        run_id="r1",
        delivery_id="d3",
        instrument="BTC-USD",
        message_kind=MessageKind.TIMER,
        receive_time_ns=8_000_000_000
    )
    dec_t2, _ = oracle.apply(t2)
    assert dec_t2.code == DecisionCode.ACCEPTED
    assert dec_t2.resulting_book_state == QualityState.STALE
    assert oracle.state == QualityState.STALE

    # 4. Fresh update arrives at t = 8_100_000_000 -> restores state to VALID!
    e2 = EventEnvelope(
        run_id="r1",
        delivery_id="d4",
        instrument="BTC-USD",
        message_kind=MessageKind.UPDATE,
        side=Side.BID,
        price_ticks=5_000_100,
        size_units=100_000_000,
        provider_sequence=2,
        receive_time_ns=8_100_000_000
    )
    dec_e2, _ = oracle.apply(e2)
    assert dec_e2.code == DecisionCode.ACCEPTED
    assert oracle.state == QualityState.VALID
