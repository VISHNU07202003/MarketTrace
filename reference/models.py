"""
MarketTrace Reference Models and Event Envelope Contract.
Defines canonical data structures matching C++ engine contracts.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageKind(str, Enum):
    SNAPSHOT = "SNAPSHOT"
    UPDATE = "UPDATE"
    TIMER = "TIMER"


class Side(str, Enum):
    NONE = "NONE"
    BID = "BID"
    ASK = "ASK"


class DecisionCode(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_INVALID_PRICE = "REJECTED_INVALID_PRICE"
    REJECTED_INVALID_SIZE = "REJECTED_INVALID_SIZE"
    REJECTED_UNKNOWN_SIDE = "REJECTED_UNKNOWN_SIDE"
    REJECTED_OUT_OF_SEQUENCE = "REJECTED_OUT_OF_SEQUENCE"
    DROPPED_DUPLICATE = "DROPPED_DUPLICATE"


class QualityState(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"
    RECOMPUTING = "RECOMPUTING"


class EventEnvelope(BaseModel):
    run_id: str
    delivery_id: str
    source: str = "synthetic_fixture"
    source_session: str = "session_001"
    instrument: str = "BTC-USD"
    message_kind: MessageKind
    
    provider_event_id: Optional[str] = None
    provider_sequence: Optional[int] = None
    provider_time_ns: Optional[int] = None
    
    receive_time_ns: int = 0
    replay_time_ns: int = 0
    
    side: Side = Side.NONE
    price_ticks: int = 0      # 1 tick = $0.01 (cents)
    size_units: int = 0       # 1 unit = 1 satoshi (1e-8 BTC)
    payload_hash: str = ""


class ProcessingDecision(BaseModel):
    delivery_id: str
    code: DecisionCode
    reason: str
    decision_time_ns: int = 0
    resulting_book_state: QualityState = QualityState.VALID


class BookMetrics(BaseModel):
    best_bid_ticks: Optional[int] = None
    best_ask_ticks: Optional[int] = None
    midpoint_ticks: Optional[int] = None
    spread_ticks: Optional[int] = None
    is_crossed: bool = False
    is_empty: bool = True
