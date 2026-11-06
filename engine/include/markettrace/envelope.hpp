#pragma once

#include <string>
#include <optional>
#include <cstdint>
#include <string_view>

namespace markettrace {

enum class MessageKind {
    Snapshot,
    Update,
    Timer
};

enum class Side {
    None,
    Bid,
    Ask
};

enum class DecisionCode {
    Accepted,
    RejectedInvalidPrice,
    RejectedInvalidSize,
    RejectedUnknownSide,
    RejectedOutOfSequence,
    DroppedDuplicate
};

enum class QualityState {
    Valid,
    Stale,
    Incomplete,
    Blocked,
    Recomputing
};

struct EventEnvelope {
    std::string run_id;
    std::string delivery_id;           // Unique arrival identifier (always unique per local delivery)
    std::string source;                // e.g., "synthetic_fixture", "coinbase_l2"
    std::string source_session;
    std::string instrument;            // e.g., "BTC-USD"
    MessageKind message_kind;
    
    std::optional<std::string> provider_event_id;
    std::optional<int64_t> provider_sequence;    // ONLY if provided by upstream feed
    std::optional<int64_t> provider_time_ns;
    
    int64_t receive_time_ns{0};
    int64_t replay_time_ns{0};
    
    Side side{Side::None};
    int64_t price_ticks{0};            // Integer scaled price (e.g. 1 tick = $0.01)
    int64_t size_units{0};             // Integer scaled size (e.g. 1 unit = 0.00000001 BTC)
    std::string payload_hash;

    // Helper conversion methods
    static std::string_view message_kind_to_string(MessageKind kind);
    static std::string_view side_to_string(Side side);
    static std::string_view decision_to_string(DecisionCode code);
    static std::string_view quality_state_to_string(QualityState state);
};

struct ProcessingDecision {
    std::string delivery_id;
    DecisionCode code{DecisionCode::Accepted};
    std::string reason;
    int64_t decision_time_ns{0};
    QualityState resulting_book_state{QualityState::Valid};
};

} // namespace markettrace
