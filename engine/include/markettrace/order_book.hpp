#pragma once

#include "envelope.hpp"
#include <map>
#include <optional>
#include <functional>
#include <cstdint>

namespace markettrace {

struct BookMetrics {
    std::optional<int64_t> best_bid_ticks;
    std::optional<int64_t> best_ask_ticks;
    std::optional<int64_t> midpoint_ticks;     // (best_bid + best_ask) / 2
    std::optional<int64_t> spread_ticks;       // best_ask - best_bid
    bool is_crossed{false};
    bool is_empty{true};
};

class OrderBook {
public:
    explicit OrderBook(std::string instrument = "BTC-USD");

    void clear();
    
    // Apply snapshot or incremental update
    ProcessingDecision apply(const EventEnvelope& event);
    
    // Read current state
    QualityState state() const { return current_state_; }
    BookMetrics metrics() const;
    const std::string& instrument() const { return instrument_; }
    
    // Inspect specific price levels (ticks -> units)
    const std::map<int64_t, int64_t, std::greater<int64_t>>& bids() const { return bids_; }
    const std::map<int64_t, int64_t, std::less<int64_t>>& asks() const { return asks_; }

private:
    std::string instrument_;
    QualityState current_state_{QualityState::Valid};
    
    // Bids sorted descending (highest first)
    std::map<int64_t, int64_t, std::greater<int64_t>> bids_;
    // Asks sorted ascending (lowest first)
    std::map<int64_t, int64_t, std::less<int64_t>> asks_;

    std::optional<int64_t> last_provider_sequence_;
    int64_t last_update_time_ns_{0};

    ProcessingDecision apply_snapshot(const EventEnvelope& event);
    ProcessingDecision apply_update(const EventEnvelope& event);
};

} // namespace markettrace
