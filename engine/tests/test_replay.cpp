#include "markettrace/replay.hpp"
#include <iostream>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace markettrace;

void test_clean_replay_parity() {
    ReplayEngine engine("BTC-USD");
    auto events = ReplayEngine::load_events_from_json("fixtures/clean_run.json");
    assert(events.size() >= 100);

    auto records = engine.replay(events);
    assert(records.size() == events.size());

    std::string failure_reason;
    bool match = ReplayEngine::verify_parity_with_reference(
        records,
        "fixtures/expected_clean_metrics.json",
        failure_reason
    );

    if (!match) {
        std::cerr << "[FAIL] Clean replay parity check failed: " << failure_reason << std::endl;
        assert(false);
    }
    std::cout << "[PASS] Clean replay decisions and metrics match reference (" << records.size() << " events)." << std::endl;
}

void test_faulted_replay_parity() {
    ReplayEngine engine("BTC-USD");
    auto events = ReplayEngine::load_events_from_json("fixtures/faulted_run.json");
    assert(events.size() >= 100);

    auto records = engine.replay(events);
    assert(records.size() == events.size());

    std::string failure_reason;
    bool match = ReplayEngine::verify_parity_with_reference(
        records,
        "fixtures/expected_faulted_metrics.json",
        failure_reason
    );

    if (!match) {
        std::cerr << "[FAIL] Faulted replay parity check failed: " << failure_reason << std::endl;
        assert(false);
    }
    std::cout << "[PASS] Faulted replay decisions and metrics match reference (" << records.size() << " events)." << std::endl;

    // Export evidence JSONL for Phase 3 ingestion
    ReplayEngine::export_evidence_jsonl(
        events,
        records,
        "fixtures/deliveries.jsonl",
        "fixtures/decisions.jsonl"
    );
    std::cout << "[PASS] Exported append-only evidence: fixtures/deliveries.jsonl and fixtures/decisions.jsonl" << std::endl;
}

void test_holdout_replay_parity() {
    ReplayEngine engine("BTC-USD");
    auto events = ReplayEngine::load_events_from_json("fixtures/holdout_faulted_run.json");
    assert(events.size() >= 100);

    auto records = engine.replay(events);
    assert(records.size() == events.size());

    std::string failure_reason;
    bool match = ReplayEngine::verify_parity_with_reference(
        records,
        "fixtures/expected_holdout_faulted_metrics.json",
        failure_reason
    );

    if (!match) {
        std::cerr << "[FAIL] Holdout replay parity check failed: " << failure_reason << std::endl;
        assert(false);
    }
    std::cout << "[PASS] Holdout replay decisions and metrics match reference (seed 101, " << records.size() << " events)." << std::endl;
}

void test_controlled_incident_replay() {
    for (const char* branch : {"clean", "damaged", "repaired"}) {
        ReplayEngine engine("BTC-USD");
        const std::string path = std::string("fixtures/incident_") + branch + ".json";
        auto events = ReplayEngine::load_events_from_json(path);
        auto records = engine.replay(events);
        std::string reason;
        assert(ReplayEngine::verify_parity_with_reference(
            records, std::string("fixtures/expected_incident_") + branch + "_metrics.json", reason
        ));
    }
    std::cout << "[PASS] Controlled missing-update and repaired branches match reference." << std::endl;
}

void test_determinism_and_benchmarks() {
    ReplayEngine engine("BTC-USD");
    auto events = ReplayEngine::load_events_from_json("fixtures/clean_run.json");

    auto run1 = engine.replay(events);
    auto run2 = engine.replay(events);

    assert(run1.size() == run2.size());
    for (size_t i = 0; i < run1.size(); ++i) {
        assert(run1[i].delivery_id == run2[i].delivery_id);
        assert(run1[i].decision.code == run2[i].decision.code);
        assert(run1[i].decision.resulting_book_state == run2[i].decision.resulting_book_state);
        assert(run1[i].metrics.midpoint_ticks == run2[i].metrics.midpoint_ticks);
        assert(run1[i].metrics.spread_ticks == run2[i].metrics.spread_ticks);
    }
    std::cout << "[PASS] Determinism: two independent replay runs produced identical outputs." << std::endl;

    // Timing a 111-event fixture inside a unit test is not a valid latency
    // benchmark. Keep performance work separate from correctness gates.
}

int main() {
    try {
        test_clean_replay_parity();
        test_faulted_replay_parity();
        test_holdout_replay_parity();
        test_controlled_incident_replay();
        test_determinism_and_benchmarks();
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[FAIL] EngineReplayTest threw exception: " << ex.what() << std::endl;
        return 1;
    }
}
