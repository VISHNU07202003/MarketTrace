#include "markettrace/envelope.hpp"
#include "markettrace/order_book.hpp"
#include <iostream>

int main() {
    std::cout << "MarketTrace Engine v0.1.0 (C++20)" << std::endl;
    std::cout << "Order-book fault replay and impact verification core" << std::endl;

    markettrace::OrderBook book("BTC-USD");
    std::cout << "Initialized book for " << book.instrument() 
              << ", status: " << markettrace::EventEnvelope::quality_state_to_string(book.state()) 
              << std::endl;

    return 0;
}
