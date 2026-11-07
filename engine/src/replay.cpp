#include "markettrace/replay.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <chrono>
#include <algorithm>
#include <iostream>
#include <sstream>

using json = nlohmann::json;

namespace markettrace {

ReplayEngine::ReplayEngine(std::string instrument)
    : instrument_(std::move(instrument)), book_(instrument_) {}

std::vector<EventEnvelope> ReplayEngine::load_events_from_json(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        // Fallback for execution from build directory
        file.open("../" + filepath);
        if (!file.is_open()) {
            throw std::runtime_error("Failed to open fixture file: " + filepath);
        }
    }

    json j;
    file >> j;

    std::vector<EventEnvelope> events;
    events.reserve(j.size());

    for (const auto& item : j) {
        EventEnvelope ev;
        ev.run_id = item.value("run_id", "");
        ev.delivery_id = item.value("delivery_id", "");
        ev.source = item.value("source", "");
        ev.source_session = item.value("source_session", "");
        ev.instrument = item.value("instrument", "");

        std::string kind_str = item.value("message_kind", "UPDATE");
        if (kind_str == "SNAPSHOT") ev.message_kind = MessageKind::Snapshot;
        else if (kind_str == "TIMER") ev.message_kind = MessageKind::Timer;
        else ev.message_kind = MessageKind::Update;

        if (item.contains("provider_event_id") && !item["provider_event_id"].is_null()) {
            ev.provider_event_id = item["provider_event_id"].get<std::string>();
        }
        if (item.contains("provider_sequence") && !item["provider_sequence"].is_null()) {
            ev.provider_sequence = item["provider_sequence"].get<int64_t>();
        }
        if (item.contains("provider_time_ns") && !item["provider_time_ns"].is_null()) {
            ev.provider_time_ns = item["provider_time_ns"].get<int64_t>();
        }

        ev.receive_time_ns = item.value("receive_time_ns", 0LL);
        ev.replay_time_ns = item.value("replay_time_ns", 0LL);

        std::string side_str = item.value("side", "NONE");
        if (side_str == "BID") ev.side = Side::Bid;
        else if (side_str == "ASK") ev.side = Side::Ask;
        else ev.side = Side::None;

        ev.price_ticks = item.value("price_ticks", 0LL);
        ev.size_units = item.value("size_units", 0LL);
        ev.payload_hash = item.value("payload_hash", "");

        events.push_back(std::move(ev));
    }

    return events;
}

std::vector<ReplayRecord> ReplayEngine::replay(const std::vector<EventEnvelope>& events) {
    book_.clear();
    std::vector<ReplayRecord> records;
    records.reserve(events.size());

    for (const auto& ev : events) {
        ProcessingDecision dec = book_.apply(ev);
        BookMetrics met = book_.metrics();
        records.push_back(ReplayRecord{ev.delivery_id, std::move(dec), met});
    }

    return records;
}

void ReplayEngine::export_records_to_json(const std::vector<ReplayRecord>& records, const std::string& filepath) {
    json j = json::array();

    for (const auto& r : records) {
        json item;
        item["delivery_id"] = r.delivery_id;

        json dec_obj;
        dec_obj["delivery_id"] = r.decision.delivery_id;
        dec_obj["code"] = std::string(EventEnvelope::decision_to_string(r.decision.code));
        dec_obj["reason"] = r.decision.reason;
        dec_obj["decision_time_ns"] = r.decision.decision_time_ns;
        dec_obj["resulting_book_state"] = std::string(EventEnvelope::quality_state_to_string(r.decision.resulting_book_state));
        item["decision"] = dec_obj;

        json met_obj;
        if (r.metrics.best_bid_ticks.has_value()) {
            met_obj["best_bid_ticks"] = *r.metrics.best_bid_ticks;
        } else {
            met_obj["best_bid_ticks"] = nullptr;
        }

        if (r.metrics.best_ask_ticks.has_value()) {
            met_obj["best_ask_ticks"] = *r.metrics.best_ask_ticks;
        } else {
            met_obj["best_ask_ticks"] = nullptr;
        }

        if (r.metrics.midpoint_ticks.has_value()) {
            met_obj["midpoint_ticks"] = *r.metrics.midpoint_ticks;
        } else {
            met_obj["midpoint_ticks"] = nullptr;
        }
        if (r.metrics.midpoint_half_ticks.has_value()) {
            met_obj["midpoint_half_ticks"] = *r.metrics.midpoint_half_ticks;
        } else {
            met_obj["midpoint_half_ticks"] = nullptr;
        }

        if (r.metrics.spread_ticks.has_value()) {
            met_obj["spread_ticks"] = *r.metrics.spread_ticks;
        } else {
            met_obj["spread_ticks"] = nullptr;
        }

        met_obj["is_crossed"] = r.metrics.is_crossed;
        met_obj["is_empty"] = r.metrics.is_empty;
        item["metrics"] = met_obj;

        j.push_back(item);
    }

    std::ofstream out(filepath);
    out << j.dump(2) << std::endl;
}

void ReplayEngine::export_evidence_jsonl(
    const std::vector<EventEnvelope>& events,
    const std::vector<ReplayRecord>& records,
    const std::string& deliveries_path,
    const std::string& decisions_path
) {
    // 1. Raw Deliveries JSONL (preserves all arrivals, including rejected ones)
    std::ofstream d_file(deliveries_path);
    for (const auto& ev : events) {
        json j;
        j["run_id"] = ev.run_id;
        j["delivery_id"] = ev.delivery_id;
        j["source"] = ev.source;
        j["source_session"] = ev.source_session;
        j["instrument"] = ev.instrument;
        j["message_kind"] = std::string(EventEnvelope::message_kind_to_string(ev.message_kind));
        if (ev.provider_sequence.has_value()) j["provider_sequence"] = *ev.provider_sequence;
        else j["provider_sequence"] = nullptr;
        j["receive_time_ns"] = ev.receive_time_ns;
        j["replay_time_ns"] = ev.replay_time_ns;
        j["side"] = std::string(EventEnvelope::side_to_string(ev.side));
        j["price_ticks"] = ev.price_ticks;
        j["size_units"] = ev.size_units;
        j["payload_hash"] = ev.payload_hash;
        d_file << j.dump() << "\n";
    }

    // 2. Decisions JSONL
    std::ofstream dec_file(decisions_path);
    for (const auto& r : records) {
        json j;
        j["delivery_id"] = r.decision.delivery_id;
        j["code"] = std::string(EventEnvelope::decision_to_string(r.decision.code));
        j["reason"] = r.decision.reason;
        j["decision_time_ns"] = r.decision.decision_time_ns;
        j["resulting_book_state"] = std::string(EventEnvelope::quality_state_to_string(r.decision.resulting_book_state));
        dec_file << j.dump() << "\n";
    }
}

BenchmarkStats ReplayEngine::benchmark(const std::vector<EventEnvelope>& events, size_t iterations) {
    if (events.empty() || iterations == 0) return BenchmarkStats{};

    // Warm-up run
    replay(events);

    std::vector<double> latencies_ns;
    latencies_ns.reserve(events.size() * iterations);

    auto start_total = std::chrono::high_resolution_clock::now();

    for (size_t it = 0; it < iterations; ++it) {
        book_.clear();
        for (const auto& ev : events) {
            auto t0 = std::chrono::high_resolution_clock::now();
            book_.apply(ev);
            book_.metrics();
            auto t1 = std::chrono::high_resolution_clock::now();
            latencies_ns.push_back(std::chrono::duration<double, std::nano>(t1 - t0).count());
        }
    }

    auto end_total = std::chrono::high_resolution_clock::now();
    double total_ms = std::chrono::duration<double, std::milli>(end_total - start_total).count();

    std::sort(latencies_ns.begin(), latencies_ns.end());
    size_t total_ops = latencies_ns.size();

    BenchmarkStats stats;
    stats.event_count = events.size();
    stats.total_elapsed_ms = total_ms;
    stats.events_per_second = (static_cast<double>(total_ops) / (total_ms / 1000.0));
    stats.p50_latency_ns = latencies_ns[total_ops * 50 / 100];
    stats.p99_latency_ns = latencies_ns[total_ops * 99 / 100];

    return stats;
}

bool ReplayEngine::verify_parity_with_reference(
    const std::vector<ReplayRecord>& actual_records,
    const std::string& reference_metrics_json_path,
    std::string& failure_reason
) {
    std::ifstream file(reference_metrics_json_path);
    if (!file.is_open()) {
        file.open("../" + reference_metrics_json_path);
        if (!file.is_open()) {
            failure_reason = "Could not open reference metrics file: " + reference_metrics_json_path;
            return false;
        }
    }

    json ref_j;
    file >> ref_j;

    if (actual_records.size() != ref_j.size()) {
        failure_reason = "Record count mismatch: actual " + std::to_string(actual_records.size()) +
                         ", expected " + std::to_string(ref_j.size());
        return false;
    }

    for (size_t i = 0; i < actual_records.size(); ++i) {
        const auto& act = actual_records[i];
        const auto& exp = ref_j[i];

        std::string exp_del_id = exp.value("delivery_id", "");
        if (act.delivery_id != exp_del_id) {
            failure_reason = "Mismatch at index " + std::to_string(i) + ": delivery_id actual " +
                             act.delivery_id + ", expected " + exp_del_id;
            return false;
        }

        const auto& exp_dec = exp["decision"];
        std::string act_code = std::string(EventEnvelope::decision_to_string(act.decision.code));
        std::string exp_code = exp_dec.value("code", "");
        if (act_code != exp_code) {
            failure_reason = "Mismatch at delivery " + act.delivery_id + ": decision code actual " +
                             act_code + ", expected " + exp_code;
            return false;
        }

        std::string act_state = std::string(EventEnvelope::quality_state_to_string(act.decision.resulting_book_state));
        std::string exp_state = exp_dec.value("resulting_book_state", "");
        if (act_state != exp_state) {
            failure_reason = "Mismatch at delivery " + act.delivery_id + ": quality state actual " +
                             act_state + ", expected " + exp_state;
            return false;
        }

        const auto& exp_met = exp["metrics"];
        if (exp_met.contains("midpoint_half_ticks")) {
            if (exp_met["midpoint_half_ticks"].is_null()) {
                if (act.metrics.midpoint_half_ticks.has_value()) {
                    failure_reason = "Unexpected exact midpoint at " + act.delivery_id;
                    return false;
                }
            } else if (!act.metrics.midpoint_half_ticks.has_value() ||
                       *act.metrics.midpoint_half_ticks != exp_met["midpoint_half_ticks"].get<int64_t>()) {
                failure_reason = "Exact half-tick midpoint mismatch at " + act.delivery_id;
                return false;
            }
        }
        // Check best bid
        if (exp_met["best_bid_ticks"].is_null()) {
            if (act.metrics.best_bid_ticks.has_value()) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": expected null best_bid_ticks";
                return false;
            }
        } else {
            int64_t exp_bid = exp_met["best_bid_ticks"].get<int64_t>();
            if (!act.metrics.best_bid_ticks.has_value() || *act.metrics.best_bid_ticks != exp_bid) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": best_bid_ticks actual " +
                                 (act.metrics.best_bid_ticks ? std::to_string(*act.metrics.best_bid_ticks) : "null") +
                                 ", expected " + std::to_string(exp_bid);
                return false;
            }
        }

        // Check best ask
        if (exp_met["best_ask_ticks"].is_null()) {
            if (act.metrics.best_ask_ticks.has_value()) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": expected null best_ask_ticks";
                return false;
            }
        } else {
            int64_t exp_ask = exp_met["best_ask_ticks"].get<int64_t>();
            if (!act.metrics.best_ask_ticks.has_value() || *act.metrics.best_ask_ticks != exp_ask) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": best_ask_ticks actual " +
                                 (act.metrics.best_ask_ticks ? std::to_string(*act.metrics.best_ask_ticks) : "null") +
                                 ", expected " + std::to_string(exp_ask);
                return false;
            }
        }

        // Check midpoint
        if (exp_met["midpoint_ticks"].is_null()) {
            if (act.metrics.midpoint_ticks.has_value()) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": expected null midpoint_ticks";
                return false;
            }
        } else {
            int64_t exp_mid = exp_met["midpoint_ticks"].get<int64_t>();
            if (!act.metrics.midpoint_ticks.has_value() || *act.metrics.midpoint_ticks != exp_mid) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": midpoint_ticks actual " +
                                 (act.metrics.midpoint_ticks ? std::to_string(*act.metrics.midpoint_ticks) : "null") +
                                 ", expected " + std::to_string(exp_mid);
                return false;
            }
        }

        // Check spread
        if (exp_met["spread_ticks"].is_null()) {
            if (act.metrics.spread_ticks.has_value()) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": expected null spread_ticks";
                return false;
            }
        } else {
            int64_t exp_spread = exp_met["spread_ticks"].get<int64_t>();
            if (!act.metrics.spread_ticks.has_value() || *act.metrics.spread_ticks != exp_spread) {
                failure_reason = "Mismatch at delivery " + act.delivery_id + ": spread_ticks actual " +
                                 (act.metrics.spread_ticks ? std::to_string(*act.metrics.spread_ticks) : "null") +
                                 ", expected " + std::to_string(exp_spread);
                return false;
            }
        }

        // Check is_crossed and is_empty
        bool exp_crossed = exp_met.value("is_crossed", false);
        if (act.metrics.is_crossed != exp_crossed) {
            failure_reason = "Mismatch at delivery " + act.delivery_id + ": is_crossed actual " +
                             std::to_string(act.metrics.is_crossed) + ", expected " + std::to_string(exp_crossed);
            return false;
        }

        bool exp_empty = exp_met.value("is_empty", true);
        if (act.metrics.is_empty != exp_empty) {
            failure_reason = "Mismatch at delivery " + act.delivery_id + ": is_empty actual " +
                             std::to_string(act.metrics.is_empty) + ", expected " + std::to_string(exp_empty);
            return false;
        }
    }

    return true;
}

} // namespace markettrace
