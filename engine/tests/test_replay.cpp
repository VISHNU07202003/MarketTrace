#include "markettrace/replay.hpp"
#include <iostream>
#include <cassert>

using namespace markettrace;

void test_clean_replay_parity() {
    ReplayEngine engine("BTC-USD");
    auto events = ReplayEngine::load_events_from_json("fixtures/clean_run.json");
    assert(events.size() == 111);

    auto records = engine.replay(events);
    assert(records.size() == 111);

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
    std::cout << "[PASS] Clean replay parity verified bit-for-bit with Python oracle (111/111 events)." << std::endl;
}

void test_faulted_replay_parity() {
    ReplayEngine engine("BTC-USD");
    auto events = ReplayEngine::load_events_from_json("fixtures/faulted_run.json");
    assert(events.size() == 113);

    auto records = engine.replay(events);
    assert(records.size() == 113);

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
    std::cout << "[PASS] Faulted replay parity verified bit-for-bit with Python oracle (113/113 events, all faults matched)." << std::endl;

    // Export evidence JSONL for Phase 3 ingestion
    ReplayEngine::export_evidence_jsonl(
        events,
        records,
        "fixtures/deliveries.jsonl",
        "fixtures/decisions.jsonl"
    );
    std::cout << "[PASS] Exported append-only evidence: fixtures/deliveries.jsonl and fixtures/decisions.jsonl" << std::endl;
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

    auto stats = engine.benchmark(events, 100);
    std::cout << "[BENCHMARK] Replay Throughput & Latency:" << std::endl;
    std::cout << "  - Events processed: " << stats.event_count * 100 << " (100 iterations of 111 events)" << std::endl;
    std::cout << "  - Total time: " << stats.total_elapsed_ms << " ms" << std::endl;
    std::cout << "  - Throughput: " << static_cast<int64_t>(stats.events_per_second) << " events/sec" << std::endl;
    std::cout << "  - Latency p50: " << stats.p50_latency_ns << " ns" << std::endl;
    std::cout << "  - Latency p99: " << stats.p99_latency_ns << " ns" << std::endl;
}

int main() {
    try {
        test_clean_replay_parity();
        test_faulted_replay_parity();
        test_determinism_and_benchmarks();
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[FAIL] EngineReplayTest threw exception: " << ex.what() << std::endl;
        return 1;
    }
}
