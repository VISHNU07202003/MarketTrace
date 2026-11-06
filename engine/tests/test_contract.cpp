#include "markettrace/envelope.hpp"
#include "markettrace/order_book.hpp"
#include <cassert>
#include <iostream>

using namespace markettrace;

void test_basic_book_contract() {
    OrderBook book("BTC-USD");
    assert(book.state() == QualityState::Valid);
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
    assert(book.state() == QualityState::Valid);

    // Add bid: 60,000.00 USD (6,000,000 ticks), size 1.5 BTC (150,000,000 satoshis)
    EventEnvelope bid_event;
    bid_event.delivery_id = "del-002";
    bid_event.instrument = "BTC-USD";
    bid_event.message_kind = MessageKind::Update;
    bid_event.side = Side::Bid;
    bid_event.price_ticks = 6'000'000;
    bid_event.size_units = 150'000'000;
    bid_event.provider_sequence = 101;
    bid_event.receive_time_ns = 1'000'001'000;

    auto dec2 = book.apply(bid_event);
    assert(dec2.code == DecisionCode::Accepted);

    // Add ask: 60,010.00 USD (6,001,000 ticks), size 2.0 BTC
    EventEnvelope ask_event;
    ask_event.delivery_id = "del-003";
    ask_event.instrument = "BTC-USD";
    ask_event.message_kind = MessageKind::Update;
    ask_event.side = Side::Ask;
    ask_event.price_ticks = 6'001'000;
    ask_event.size_units = 200'000'000;
    ask_event.provider_sequence = 102;
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
    assert(book.state() == QualityState::Valid);

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
