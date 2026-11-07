#include "markettrace/envelope.hpp"
#include "markettrace/order_book.hpp"
#include "markettrace/replay.hpp"
#include <iostream>
#include <string>
#include <filesystem>

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

        if (argc == 4 && std::string(argv[2]) == "--output") {
            const std::filesystem::path output(argv[3]);
            if (output.has_parent_path()) std::filesystem::create_directories(output.parent_path());
            markettrace::ReplayEngine::export_records_to_json(records, output.string());
            std::cout << "[OUTPUT] Wrote engine decisions and checkpoints: " << output << std::endl;
        } else if (argc > 2) {
            std::cerr << "Usage: markettrace_cli [fixture.json] [--output result.json]" << std::endl;
            return 2;
        }

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
