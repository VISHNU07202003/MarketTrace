#include "markettrace/envelope.hpp"
#include "markettrace/order_book.hpp"
#include "markettrace/replay.hpp"
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    std::cout << "==========================================================" << std::endl;
    std::cout << " MarketTrace Engine v0.1.0 (C++20)" << std::endl;
    std::cout << " Order-Book Replay & Incident Verification Core" << std::endl;
    std::cout << "==========================================================" << std::endl;

    std::string fixture_file = "fixtures/clean_run.json";
    if (argc > 1) {
        fixture_file = argv[1];
    }

    try {
        std::cout << "[INFO] Loading fixture: " << fixture_file << std::endl;
        auto events = markettrace::ReplayEngine::load_events_from_json(fixture_file);
        std::cout << "[INFO] Loaded " << events.size() << " events." << std::endl;

        markettrace::ReplayEngine engine("BTC-USD");
        auto records = engine.replay(events);
        std::cout << "[INFO] Replay completed. Generated " << records.size() << " records." << std::endl;

        size_t accepted = 0;
        size_t rejected = 0;
        for (const auto& r : records) {
            if (r.decision.code == markettrace::DecisionCode::Accepted) accepted++;
            else rejected++;
        }

        std::cout << "[SUMMARY] Processed: " << records.size() 
                  << " | Accepted: " << accepted 
                  << " | Rejected/Dropped: " << rejected 
                  << " | Final Book State: " 
                  << markettrace::EventEnvelope::quality_state_to_string(records.back().decision.resulting_book_state)
                  << std::endl;

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[ERROR] " << ex.what() << std::endl;
        return 1;
    }
}
