#include "markettrace/order_book.hpp"

namespace markettrace {

OrderBook::OrderBook(std::string instrument)
    : instrument_(std::move(instrument)) {}

void OrderBook::clear() {
    bids_.clear();
    asks_.clear();
    current_state_ = QualityState::Valid;
    last_provider_sequence_.reset();
    last_update_time_ns_ = 0;
}

ProcessingDecision OrderBook::apply(const EventEnvelope& event) {
    if (event.instrument != instrument_) {
        ProcessingDecision dec;
        dec.delivery_id = event.delivery_id;
        dec.code = DecisionCode::RejectedUnknownSide;
        dec.reason = "Instrument mismatch: expected " + instrument_ + ", got " + event.instrument;
        dec.decision_time_ns = event.receive_time_ns;
        dec.resulting_book_state = current_state_;
        return dec;
    }

    if (event.message_kind == MessageKind::Snapshot) {
        return apply_snapshot(event);
    } else if (event.message_kind == MessageKind::Update) {
        return apply_update(event);
    } else if (event.message_kind == MessageKind::Timer) {
        ProcessingDecision dec;
        dec.delivery_id = event.delivery_id;
        dec.code = DecisionCode::Accepted;
        dec.reason = "Timer heartbeat evaluated";
        dec.decision_time_ns = event.receive_time_ns;
        dec.resulting_book_state = current_state_;
        return dec;
    }

    ProcessingDecision dec;
    dec.delivery_id = event.delivery_id;
    dec.code = DecisionCode::RejectedUnknownSide;
    dec.reason = "Unsupported message kind";
    dec.decision_time_ns = event.receive_time_ns;
    dec.resulting_book_state = current_state_;
    return dec;
}

ProcessingDecision OrderBook::apply_snapshot(const EventEnvelope& event) {
    ProcessingDecision dec;
    dec.delivery_id = event.delivery_id;
    dec.decision_time_ns = event.receive_time_ns;

    // Snapshot resets the current book state
    // Note: If multiple levels are provided in a snapshot stream, the first clears, subsequent add.
    // For a single snapshot event or resync event:
    if (event.side == Side::None && event.price_ticks == 0 && event.size_units == 0) {
        // Reset message
        clear();
        if (event.provider_sequence.has_value()) {
            last_provider_sequence_ = event.provider_sequence;
        }
        dec.code = DecisionCode::Accepted;
        dec.reason = "Snapshot book reset initialized";
        dec.resulting_book_state = QualityState::Valid;
        current_state_ = QualityState::Valid;
        return dec;
    }

    if (event.price_ticks <= 0) {
        dec.code = DecisionCode::RejectedInvalidPrice;
        dec.reason = "Snapshot price ticks must be positive";
        dec.resulting_book_state = current_state_;
        return dec;
    }

    if (event.size_units < 0) {
        dec.code = DecisionCode::RejectedInvalidSize;
        dec.reason = "Snapshot size units must be non-negative";
        dec.resulting_book_state = current_state_;
        return dec;
    }

    if (event.side == Side::Bid) {
        if (event.size_units == 0) bids_.erase(event.price_ticks);
        else bids_[event.price_ticks] = event.size_units;
    } else if (event.side == Side::Ask) {
        if (event.size_units == 0) asks_.erase(event.price_ticks);
        else asks_[event.price_ticks] = event.size_units;
    } else {
        dec.code = DecisionCode::RejectedUnknownSide;
        dec.reason = "Snapshot side must be Bid or Ask";
        dec.resulting_book_state = current_state_;
        return dec;
    }

    if (event.provider_sequence.has_value()) {
        last_provider_sequence_ = event.provider_sequence;
    }
    current_state_ = QualityState::Valid;
    dec.code = DecisionCode::Accepted;
    dec.reason = "Snapshot level applied";
    dec.resulting_book_state = QualityState::Valid;
    return dec;
}

ProcessingDecision OrderBook::apply_update(const EventEnvelope& event) {
    ProcessingDecision dec;
    dec.delivery_id = event.delivery_id;
    dec.decision_time_ns = event.receive_time_ns;

    // 1. Sequence check (if provider sequence provided)
    if (event.provider_sequence.has_value() && last_provider_sequence_.has_value()) {
        int64_t expected_seq = *last_provider_sequence_ + 1;
        int64_t actual_seq = *event.provider_sequence;

        if (actual_seq < expected_seq) {
            dec.code = DecisionCode::DroppedDuplicate;
            dec.reason = "Stale or duplicate sequence: " + std::to_string(actual_seq) + 
                         " <= " + std::to_string(*last_provider_sequence_);
            dec.resulting_book_state = current_state_;
            return dec;
        }

        if (actual_seq > expected_seq) {
            // Gap detected!
            dec.code = DecisionCode::RejectedOutOfSequence;
            dec.reason = "Sequence gap detected: expected " + std::to_string(expected_seq) + 
                         ", got " + std::to_string(actual_seq);
            current_state_ = QualityState::Incomplete;
            dec.resulting_book_state = QualityState::Incomplete;
            last_provider_sequence_ = actual_seq;
            return dec;
        }
    }

    if (event.provider_sequence.has_value()) {
        last_provider_sequence_ = event.provider_sequence;
    }
    last_update_time_ns_ = event.receive_time_ns;

    // 2. Validate price
    if (event.price_ticks <= 0) {
        dec.code = DecisionCode::RejectedInvalidPrice;
        dec.reason = "Price ticks must be positive: " + std::to_string(event.price_ticks);
        dec.resulting_book_state = current_state_;
        return dec;
    }

    // 3. Validate size
    if (event.size_units < 0) {
        dec.code = DecisionCode::RejectedInvalidSize;
        dec.reason = "Size units cannot be negative: " + std::to_string(event.size_units);
        dec.resulting_book_state = current_state_;
        return dec;
    }

    // 4. Validate side
    if (event.side == Side::Bid) {
        if (event.size_units == 0) {
            bids_.erase(event.price_ticks);
        } else {
            bids_[event.price_ticks] = event.size_units;
        }
    } else if (event.side == Side::Ask) {
        if (event.size_units == 0) {
            asks_.erase(event.price_ticks);
        } else {
            asks_[event.price_ticks] = event.size_units;
        }
    } else {
        dec.code = DecisionCode::RejectedUnknownSide;
        dec.reason = "Update side must be Bid or Ask";
        dec.resulting_book_state = current_state_;
        return dec;
    }

    if (event.provider_sequence.has_value()) {
        last_provider_sequence_ = event.provider_sequence;
    }
    last_update_time_ns_ = event.receive_time_ns;

    dec.code = DecisionCode::Accepted;
    dec.reason = "Update applied successfully";
    dec.resulting_book_state = current_state_;
    return dec;
}

BookMetrics OrderBook::metrics() const {
    BookMetrics m;
    if (!bids_.empty()) {
        m.best_bid_ticks = bids_.begin()->first;
    }
    if (!asks_.empty()) {
        m.best_ask_ticks = asks_.begin()->first;
    }

    m.is_empty = (!m.best_bid_ticks.has_value() || !m.best_ask_ticks.has_value());

    if (!m.is_empty) {
        int64_t b = *m.best_bid_ticks;
        int64_t a = *m.best_ask_ticks;
        m.is_crossed = (b >= a);
        m.spread_ticks = a - b;
        m.midpoint_ticks = (a + b) / 2;
    }

    return m;
}

} // namespace markettrace
