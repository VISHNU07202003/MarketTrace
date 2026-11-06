"""
MarketTrace Independent Python Reference Oracle.
Provides the source of truth for order-book reconstruction,
validation rules, and financial calculation metrics.
"""

from typing import Dict, List, Optional, Tuple
import math
from reference.models import (
    EventEnvelope,
    MessageKind,
    Side,
    DecisionCode,
    QualityState,
    ProcessingDecision,
    BookMetrics
)


class ReferenceOracle:
    FRESHNESS_TIMEOUT_NS: int = 5_000_000_000  # 5 seconds staleness threshold

    def __init__(self, instrument: str = "BTC-USD"):
        self.instrument = instrument
        self.state = QualityState.VALID
        self.bids: Dict[int, int] = {}  # price_ticks -> size_units
        self.asks: Dict[int, int] = {}  # price_ticks -> size_units
        self.last_provider_sequence: Optional[int] = None
        self.last_update_time_ns: int = 0
        self.current_session: Optional[str] = None
        self.history_records: List[Tuple[ProcessingDecision, BookMetrics]] = []
        
        # Sampling history for rolling volatility: (timestamp_ns, midpoint_ticks)
        self.sampled_midpoints: List[Tuple[int, int]] = []

    def clear(self):
        self.bids.clear()
        self.asks.clear()
        self.state = QualityState.VALID
        self.last_provider_sequence = None
        self.last_update_time_ns = 0
        self.current_session = None
        self.sampled_midpoints.clear()

    def apply(self, event: EventEnvelope) -> Tuple[ProcessingDecision, BookMetrics]:
        if event.instrument != self.instrument:
            dec = ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_UNKNOWN_SIDE,
                reason=f"Instrument mismatch: expected {self.instrument}, got {event.instrument}",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )
            metrics = self.compute_metrics()
            self.history_records.append((dec, metrics))
            return dec, metrics

        if event.message_kind == MessageKind.SNAPSHOT:
            dec = self._apply_snapshot(event)
        elif event.message_kind == MessageKind.UPDATE:
            dec = self._apply_update(event)
        elif event.message_kind == MessageKind.TIMER:
            elapsed = (event.receive_time_ns - self.last_update_time_ns) if self.last_update_time_ns > 0 else 0
            if self.last_update_time_ns > 0 and elapsed > self.FRESHNESS_TIMEOUT_NS:
                self.state = QualityState.STALE
                dec = ProcessingDecision(
                    delivery_id=event.delivery_id,
                    code=DecisionCode.ACCEPTED,
                    reason=f"Staleness threshold exceeded: elapsed {elapsed}ns > {self.FRESHNESS_TIMEOUT_NS}ns",
                    decision_time_ns=event.receive_time_ns,
                    resulting_book_state=QualityState.STALE
                )
            else:
                dec = ProcessingDecision(
                    delivery_id=event.delivery_id,
                    code=DecisionCode.ACCEPTED,
                    reason="Timer heartbeat evaluated; feed fresh",
                    decision_time_ns=event.receive_time_ns,
                    resulting_book_state=self.state
                )
        else:
            dec = ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_UNKNOWN_SIDE,
                reason=f"Unknown message kind: {event.message_kind}",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        metrics = self.compute_metrics()
        self.history_records.append((dec, metrics))
        return dec, metrics

    def _apply_snapshot(self, event: EventEnvelope) -> ProcessingDecision:
        # Full reset message
        if event.side == Side.NONE and event.price_ticks == 0 and event.size_units == 0:
            self.bids.clear()
            self.asks.clear()
            self.state = QualityState.VALID
            if event.provider_sequence is not None:
                self.last_provider_sequence = event.provider_sequence
            self.last_update_time_ns = event.receive_time_ns
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.ACCEPTED,
                reason="Snapshot book reset",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=QualityState.VALID
            )

        if event.price_ticks <= 0:
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_INVALID_PRICE,
                reason=f"Snapshot price must be positive, got {event.price_ticks}",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        if event.size_units < 0:
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_INVALID_SIZE,
                reason=f"Snapshot size must be non-negative, got {event.size_units}",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        if event.side == Side.BID:
            if event.size_units == 0:
                self.bids.pop(event.price_ticks, None)
            else:
                self.bids[event.price_ticks] = event.size_units
        elif event.side == Side.ASK:
            if event.size_units == 0:
                self.asks.pop(event.price_ticks, None)
            else:
                self.asks[event.price_ticks] = event.size_units
        else:
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_UNKNOWN_SIDE,
                reason="Snapshot side must be BID or ASK",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        if event.provider_sequence is not None:
            self.last_provider_sequence = event.provider_sequence
        self.state = QualityState.VALID
        self.last_update_time_ns = event.receive_time_ns

        return ProcessingDecision(
            delivery_id=event.delivery_id,
            code=DecisionCode.ACCEPTED,
            reason="Snapshot level applied",
            decision_time_ns=event.receive_time_ns,
            resulting_book_state=QualityState.VALID
        )

    def _apply_update(self, event: EventEnvelope) -> ProcessingDecision:
        # Check sequence
        if event.provider_sequence is not None and self.last_provider_sequence is not None:
            expected = self.last_provider_sequence + 1
            actual = event.provider_sequence

            if actual < expected:
                return ProcessingDecision(
                    delivery_id=event.delivery_id,
                    code=DecisionCode.DROPPED_DUPLICATE,
                    reason=f"Duplicate sequence: {actual} <= {self.last_provider_sequence}",
                    decision_time_ns=event.receive_time_ns,
                    resulting_book_state=self.state
                )

            if actual > expected:
                self.state = QualityState.INCOMPLETE
                self.last_provider_sequence = actual
                return ProcessingDecision(
                    delivery_id=event.delivery_id,
                    code=DecisionCode.REJECTED_OUT_OF_SEQUENCE,
                    reason=f"Sequence gap: expected {expected}, got {actual}",
                    decision_time_ns=event.receive_time_ns,
                    resulting_book_state=QualityState.INCOMPLETE
                )

        if event.provider_sequence is not None:
            self.last_provider_sequence = event.provider_sequence

        if event.price_ticks <= 0:
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_INVALID_PRICE,
                reason=f"Price ticks must be positive, got {event.price_ticks}",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        if event.size_units < 0:
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_INVALID_SIZE,
                reason=f"Size units cannot be negative, got {event.size_units}",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        if event.side == Side.BID:
            if event.size_units == 0:
                self.bids.pop(event.price_ticks, None)
            else:
                self.bids[event.price_ticks] = event.size_units
        elif event.side == Side.ASK:
            if event.size_units == 0:
                self.asks.pop(event.price_ticks, None)
            else:
                self.asks[event.price_ticks] = event.size_units
        else:
            return ProcessingDecision(
                delivery_id=event.delivery_id,
                code=DecisionCode.REJECTED_UNKNOWN_SIDE,
                reason="Update side must be BID or ASK",
                decision_time_ns=event.receive_time_ns,
                resulting_book_state=self.state
            )

        if self.state == QualityState.STALE:
            self.state = QualityState.VALID
        self.last_update_time_ns = event.receive_time_ns

        return ProcessingDecision(
            delivery_id=event.delivery_id,
            code=DecisionCode.ACCEPTED,
            reason="Update applied successfully",
            decision_time_ns=event.receive_time_ns,
            resulting_book_state=self.state
        )

    def compute_metrics(self) -> BookMetrics:
        best_bid = max(self.bids.keys()) if self.bids else None
        best_ask = min(self.asks.keys()) if self.asks else None

        if best_bid is None or best_ask is None:
            return BookMetrics(
                best_bid_ticks=best_bid,
                best_ask_ticks=best_ask,
                midpoint_ticks=None,
                spread_ticks=None,
                is_crossed=False,
                is_empty=True
            )

        is_crossed = best_bid >= best_ask
        spread = best_ask - best_bid
        midpoint = (best_bid + best_ask) // 2

        return BookMetrics(
            best_bid_ticks=best_bid,
            best_ask_ticks=best_ask,
            midpoint_ticks=midpoint,
            spread_ticks=spread,
            is_crossed=is_crossed,
            is_empty=False
        )

    @staticmethod
    def calculate_rolling_volatility(midpoints: List[float]) -> Optional[float]:
        """
        Calculates sample standard deviation of log returns across 11 consecutive
        valid observations (producing 10 log returns):
            r_i = ln(m_i / m_{i-1})
            vol = sqrt( sum((r_i - mean_r)^2) / 9 )
        Returns None if fewer than 11 observations or any observation is nonpositive.
        """
        if len(midpoints) != 11:
            return None

        if any(m <= 0 for m in midpoints):
            return None

        returns: List[float] = []
        for i in range(1, 11):
            r = math.log(midpoints[i] / midpoints[i - 1])
            returns.append(r)

        mean_r = sum(returns) / 10.0
        var = sum((r - mean_r) ** 2 for r in returns) / 9.0  # Sample variance (N-1)
        return math.sqrt(var)
