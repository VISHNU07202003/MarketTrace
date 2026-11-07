#include "markettrace/envelope.hpp"
#include "markettrace/order_book.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <iostream>

using namespace markettrace;

void test_basic_book_contract() {
    OrderBook book("BTC-USD");
    assert(book.state() == QualityState::Incomplete);
    assert(book.metrics().is_empty);

    // Apply snapshot initialization
    EventEnvelope snap_reset;
    snap_reset.delivery_id = "del-001";
    snap_reset.instrument = "BTC-USD";
    snap_reset.message_kind = MessageKind::Snapshot;
    snap_reset.side = Side::None;
    snap_reset.price_ticks = 0;
    snap_reset.size_units = 0;
    snap_reset.provider_sequence = 100;
    snap_reset.receive_time_ns = 1'000'000'000;
    
    auto dec1 = book.apply(snap_reset);
    assert(dec1.code == DecisionCode::Accepted);
    assert(book.state() == QualityState::Incomplete);

    // Add bid: 60,000.00 USD (6,000,000 ticks), size 1.5 BTC (150,000,000 satoshis)
    EventEnvelope bid_event;
    bid_event.delivery_id = "del-002";
    bid_event.instrument = "BTC-USD";
    bid_event.message_kind = MessageKind::Snapshot;
    bid_event.side = Side::Bid;
    bid_event.price_ticks = 6'000'000;
    bid_event.size_units = 150'000'000;
    bid_event.provider_sequence = 100;
    bid_event.receive_time_ns = 1'000'001'000;

    auto dec2 = book.apply(bid_event);
    assert(dec2.code == DecisionCode::Accepted);

    // Add ask: 60,010.00 USD (6,001,000 ticks), size 2.0 BTC
    EventEnvelope ask_event;
    ask_event.delivery_id = "del-003";
    ask_event.instrument = "BTC-USD";
    ask_event.message_kind = MessageKind::Snapshot;
    ask_event.side = Side::Ask;
    ask_event.price_ticks = 6'001'000;
    ask_event.size_units = 200'000'000;
    ask_event.provider_sequence = 100;
    ask_event.receive_time_ns = 1'000'002'000;

    auto dec3 = book.apply(ask_event);
    assert(dec3.code == DecisionCode::Accepted);

    auto m = book.metrics();
    assert(!m.is_empty);
    assert(!m.is_crossed);
    assert(*m.best_bid_ticks == 6'000'000);
    assert(*m.best_ask_ticks == 6'001'000);
    assert(*m.spread_ticks == 1'000);
    assert(*m.midpoint_ticks == 6'000'500);
    assert(*m.midpoint_half_ticks == 12'001'000);

    EventEnvelope valid_update = bid_event;
    valid_update.message_kind = MessageKind::Update;
    valid_update.provider_sequence = 101;
    valid_update.delivery_id = "valid-101";
    assert(book.apply(valid_update).code == DecisionCode::Accepted);
    valid_update.provider_sequence = 102;
    valid_update.delivery_id = "valid-102";
    assert(book.apply(valid_update).code == DecisionCode::Accepted);

    // Sequence gap detection: inject sequence 105 (missing 103, 104)
    EventEnvelope gap_event;
    gap_event.delivery_id = "del-004";
    gap_event.instrument = "BTC-USD";
    gap_event.message_kind = MessageKind::Update;
    gap_event.side = Side::Bid;
    gap_event.price_ticks = 6'000'100;
    gap_event.size_units = 50'000'000;
    gap_event.provider_sequence = 105; // Gap!
    gap_event.receive_time_ns = 1'000'005'000;

    auto dec4 = book.apply(gap_event);
    assert(dec4.code == DecisionCode::RejectedOutOfSequence);
    assert(dec4.resulting_book_state == QualityState::Incomplete);
    assert(book.state() == QualityState::Incomplete);

    // Resync via fresh snapshot resets validity
    EventEnvelope resync_snap;
    resync_snap.delivery_id = "del-005";
    resync_snap.instrument = "BTC-USD";
    resync_snap.message_kind = MessageKind::Snapshot;
    resync_snap.side = Side::None;
    resync_snap.price_ticks = 0;
    resync_snap.size_units = 0;
    resync_snap.provider_sequence = 200;
    resync_snap.receive_time_ns = 1'000'010'000;

    auto dec5 = book.apply(resync_snap);
    assert(dec5.code == DecisionCode::Accepted);
    assert(book.state() == QualityState::Incomplete);

    auto complete_snapshot = [&](int64_t seq) {
        auto b = bid_event;
        b.provider_sequence = seq;
        auto a = ask_event;
        a.provider_sequence = seq;
        assert(book.apply(b).code == DecisionCode::Accepted);
        assert(book.apply(a).code == DecisionCode::Accepted);
        assert(book.state() == QualityState::Valid);
    };
    complete_snapshot(200);

    // Negative validation tests:
    EventEnvelope bad_price;
    bad_price.delivery_id = "del-006";
    bad_price.instrument = "BTC-USD";
    bad_price.message_kind = MessageKind::Update;
    bad_price.side = Side::Bid;
    bad_price.price_ticks = -500;
    bad_price.size_units = 100;
    bad_price.provider_sequence = 201;

    auto dec6 = book.apply(bad_price);
    assert(dec6.code == DecisionCode::RejectedInvalidPrice);
    assert(book.state() == QualityState::Incomplete);
    auto ignored = valid_update;
    ignored.provider_sequence = 202;
    assert(book.apply(ignored).code == DecisionCode::RejectedOutOfSequence);

    resync_snap.provider_sequence = 201;
    assert(book.apply(resync_snap).code == DecisionCode::Accepted);
    complete_snapshot(201);

    EventEnvelope bad_size;
    bad_size.delivery_id = "del-007";
    bad_size.instrument = "BTC-USD";
    bad_size.message_kind = MessageKind::Update;
    bad_size.side = Side::Bid;
    bad_size.price_ticks = 6'000'000;
    bad_size.size_units = -10;
    bad_size.provider_sequence = 202;

    auto dec7 = book.apply(bad_size);
    assert(dec7.code == DecisionCode::RejectedInvalidSize);
    resync_snap.provider_sequence = 202;
    assert(book.apply(resync_snap).code == DecisionCode::Accepted);
    complete_snapshot(202);

    // Timer-based freshness & staleness check:
    // Update at t = 2,000,000,000 ns
    EventEnvelope good_update;
    good_update.delivery_id = "del-008";
    good_update.instrument = "BTC-USD";
    good_update.message_kind = MessageKind::Update;
    good_update.side = Side::Bid;
    good_update.price_ticks = 6'000'000;
    good_update.size_units = 100'000'000;
    good_update.provider_sequence = 203;
    good_update.receive_time_ns = 2'000'000'000;
    auto dec8 = book.apply(good_update);
    assert(dec8.code == DecisionCode::Accepted);
    assert(book.state() == QualityState::Valid);

    // Timer heartbeat at t = 3,000,000,000 ns (elapsed 1s <= 5s) -> stays VALID
    EventEnvelope fresh_timer;
    fresh_timer.delivery_id = "del-009";
    fresh_timer.instrument = "BTC-USD";
    fresh_timer.message_kind = MessageKind::Timer;
    fresh_timer.receive_time_ns = 3'000'000'000;
    auto dec9 = book.apply(fresh_timer);
    assert(dec9.code == DecisionCode::Accepted);
    assert(book.state() == QualityState::Valid);

    // Timer heartbeat at t = 9,000,000,000 ns (elapsed 7s > 5s) -> transitions to STALE!
    EventEnvelope stale_timer;
    stale_timer.delivery_id = "del-010";
    stale_timer.instrument = "BTC-USD";
    stale_timer.message_kind = MessageKind::Timer;
    stale_timer.receive_time_ns = 9'000'000'000;
    auto dec10 = book.apply(stale_timer);
    assert(dec10.code == DecisionCode::Accepted);
    assert(dec10.resulting_book_state == QualityState::Stale);
    assert(book.state() == QualityState::Stale);

    // Fresh update arrives at t = 9_100_000_000 ns -> restores state to VALID!
    EventEnvelope restore_update;
    restore_update.delivery_id = "del-011";
    restore_update.instrument = "BTC-USD";
    restore_update.message_kind = MessageKind::Update;
    restore_update.side = Side::Bid;
    restore_update.price_ticks = 6'000'100;
    restore_update.size_units = 100'000'000;
    restore_update.provider_sequence = 204;
    restore_update.receive_time_ns = 9'100'000'000;
    auto dec11 = book.apply(restore_update);
    assert(dec11.code == DecisionCode::Accepted);
    assert(book.state() == QualityState::Valid);

    std::cout << "[PASS] EngineContractTest: All C++ order-book contract assertions verified successfully." << std::endl;
}

int main() {
    try {
        test_basic_book_contract();
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[FAIL] EngineContractTest failed: " << ex.what() << std::endl;
        return 1;
    }
}
