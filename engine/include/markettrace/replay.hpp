#pragma once

#include "envelope.hpp"
#include "order_book.hpp"
#include <vector>
#include <string>
#include <memory>

namespace markettrace {

struct ReplayRecord {
    std::string delivery_id;
    ProcessingDecision decision;
    BookMetrics metrics;
};

struct BenchmarkStats {
    size_t event_count{0};
    double total_elapsed_ms{0.0};
    double events_per_second{0.0};
    double p50_latency_ns{0.0};
    double p99_latency_ns{0.0};
};

class ReplayEngine {
public:
    explicit ReplayEngine(std::string instrument = "BTC-USD");

    // Load events from JSON file
    static std::vector<EventEnvelope> load_events_from_json(const std::string& filepath);

    // Run replay over a sequence of events
    std::vector<ReplayRecord> replay(const std::vector<EventEnvelope>& events);

    // Export replay records to JSON
    static void export_records_to_json(const std::vector<ReplayRecord>& records, const std::string& filepath);

    // Export raw deliveries and decisions to JSON Lines for Phase 3 warehouse ingestion
    static void export_evidence_jsonl(
        const std::vector<EventEnvelope>& events,
        const std::vector<ReplayRecord>& records,
        const std::string& deliveries_path,
        const std::string& decisions_path
    );

    // Benchmark replay execution
    BenchmarkStats benchmark(const std::vector<EventEnvelope>& events, size_t iterations = 5);

    // Compare with expected metrics JSON file
    static bool verify_parity_with_reference(
        const std::vector<ReplayRecord>& actual_records,
        const std::string& reference_metrics_json_path,
        std::string& failure_reason
    );

private:
    std::string instrument_;
    OrderBook book_;
};

} // namespace markettrace
