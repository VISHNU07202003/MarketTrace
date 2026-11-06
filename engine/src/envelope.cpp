#include "markettrace/envelope.hpp"

namespace markettrace {

std::string_view EventEnvelope::message_kind_to_string(MessageKind kind) {
    switch (kind) {
        case MessageKind::Snapshot: return "SNAPSHOT";
        case MessageKind::Update:   return "UPDATE";
        case MessageKind::Timer:    return "TIMER";
    }
    return "UNKNOWN";
}

std::string_view EventEnvelope::side_to_string(Side side) {
    switch (side) {
        case Side::Bid:  return "BID";
        case Side::Ask:  return "ASK";
        case Side::None: return "NONE";
    }
    return "UNKNOWN";
}

std::string_view EventEnvelope::decision_to_string(DecisionCode code) {
    switch (code) {
        case DecisionCode::Accepted:               return "ACCEPTED";
        case DecisionCode::RejectedInvalidPrice:   return "REJECTED_INVALID_PRICE";
        case DecisionCode::RejectedInvalidSize:    return "REJECTED_INVALID_SIZE";
        case DecisionCode::RejectedUnknownSide:    return "REJECTED_UNKNOWN_SIDE";
        case DecisionCode::RejectedOutOfSequence:  return "REJECTED_OUT_OF_SEQUENCE";
        case DecisionCode::DroppedDuplicate:       return "DROPPED_DUPLICATE";
    }
    return "UNKNOWN";
}

std::string_view EventEnvelope::quality_state_to_string(QualityState state) {
    switch (state) {
        case QualityState::Valid:        return "VALID";
        case QualityState::Stale:        return "STALE";
        case QualityState::Incomplete:   return "INCOMPLETE";
        case QualityState::Blocked:      return "BLOCKED";
        case QualityState::Recomputing:  return "RECOMPUTING";
    }
    return "UNKNOWN";
}

} // namespace markettrace
