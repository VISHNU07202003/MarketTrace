"""Local, synthetic-only MarketTrace investigation API."""

import http.server
import json
import socketserver
import urllib.parse
from pathlib import Path

from app.data import ROOT, load_branch, analytical_rows
from depgraph.impact_analyzer import ImpactAnalyzer


class MarketTraceHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).resolve().parent), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return super().do_GET()
        params = urllib.parse.parse_qs(parsed.query)
        try:
            body = self.api(parsed.path, params)
            code = 200
        except ValueError as exc:
            body, code = {"error": str(exc)}, 400
        except KeyError as exc:
            body, code = {"error": str(exc)}, 404
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def api(self, path, params):
        branch = params.get("type", ["damaged"])[0]
        if path == "/api/status":
            return {"system": "MarketTrace", "version": "v0.2.0",
                    "mode": "OFFLINE SYNTHETIC", "data_mode": "SYNTHETIC",
                    "cloud_status": "SNOWFLAKE NOT VERIFIED"}
        if path == "/api/recovery-comparison":
            return recovery_comparison()
        events, records, source = load_branch(branch)
        if path == "/api/run-overview":
            last = records[-1]
            metrics = last["metrics"]
            return {"run_id": events[0]["run_id"], "run_type": branch,
                    "data_badge": "SYNTHETIC FIXTURE", "record_source": source,
                    "total_events": len(events),
                    "accepted_count": sum(r["decision"]["code"] == "ACCEPTED" for r in records),
                    "rejected_count": sum(r["decision"]["code"] != "ACCEPTED" for r in records),
                    "current_book_state": last["decision"]["resulting_book_state"],
                    "instrument": "BTC-USD", "best_bid_ticks": metrics["best_bid_ticks"],
                    "best_ask_ticks": metrics["best_ask_ticks"],
                    "midpoint_half_ticks": metrics.get("midpoint_half_ticks"),
                    "spread_ticks": metrics["spread_ticks"],
                    "is_crossed": metrics["is_crossed"]}
        if path == "/api/timeline":
            return {"timeline": [{**ev,
                    "decision_code": rec["decision"]["code"],
                    "decision_reason": rec["decision"]["reason"],
                    "resulting_book_state": rec["decision"]["resulting_book_state"],
                    "midpoint_half_ticks": rec["metrics"].get("midpoint_half_ticks"),
                    "spread_ticks": rec["metrics"].get("spread_ticks")}
                for ev, rec in zip(events, records)], "record_source": source}
        if path == "/api/incident-detail":
            delivery_id = params.get("delivery_id", ["inc_0061"])[0]
            index = next((i for i, ev in enumerate(events) if ev["delivery_id"] == delivery_id), None)
            if index is None:
                raise KeyError(f"Unknown delivery: {delivery_id}")
            event, record = events[index], records[index]
            history = [{"delivery_id": ev["delivery_id"],
                        "timestamp_ns": ev["replay_time_ns"],
                        "decision_code": rec["decision"]["code"],
                        "book_state": rec["decision"]["resulting_book_state"],
                        "message_kind": ev["message_kind"]}
                       for ev, rec in zip(events, records)]
            analyzer = ImpactAnalyzer()
            analyzer.build_graph_from_records(history)
            analytics, _ = analytical_rows(branch)
            chain = []
            for prefix in ("raw", "book", "quotes", "mid", "ret", "vol"):
                node = analyzer.graph.nodes.get(f"{prefix}_{delivery_id}")
                if node is None:
                    continue
                entry = node.to_dict()
                metric = "ROLLING_VOLATILITY" if prefix == "vol" else "MIDPOINT" if prefix == "mid" else None
                result = analytics.get((metric, delivery_id)) if metric else None
                if result:
                    entry["quality_state"] = result["status"]
                    entry["time_window"] = [result["window_start_ns"], result["window_end_ns"]]
                chain.append({"node_id": entry["node_id"], "stage": entry["kind"],
                              "status": entry["quality_state"], "time_window": entry["time_window"],
                              "units": "half-ticks" if prefix == "mid" else "event / sample",
                              "desc": entry["explanation"]})
            # A reset is not a completed book; use the last accepted snapshot
            # level at which the engine explicitly reported VALID.
            anchor = next((ev for ev, rec in reversed(list(zip(events[:index], records[:index])))
                           if ev["message_kind"] == "SNAPSHOT" and
                           rec["decision"]["resulting_book_state"] == "VALID"), None)
            injected = ("SEQUENCE_GAP" if delivery_id == "inc_0061" and branch == "damaged" else None)
            return {"delivery_id": delivery_id, "event": event,
                    "decision": record["decision"], "metrics": record["metrics"],
                    "record_source": source,
                    "nearest_snapshot": anchor,
                    "source_classification": "SYNTHETIC_FAULT_INJECTION" if injected else "SYNTHETIC_DELIVERY",
                    "injected_fault_info": {"fault_type": injected, "comment": "Synthetic event inc_0060 withheld"} if injected else None,
                    "depgraph_chain": chain,
                    "volatility_result": analytics.get(("ROLLING_VOLATILITY", delivery_id))}
        raise KeyError(f"Unknown endpoint: {path}")


def recovery_comparison():
    branches = {name: load_branch(name) for name in ("clean", "damaged", "repaired")}
    analytics = {name: analytical_rows(name)[0] for name in branches}
    clean_events = branches["clean"][0]
    rows = []
    for event in clean_events:
        if event["message_kind"] != "UPDATE":
            continue
        delivery_id = event["delivery_id"]
        values = {name: analytics[name].get(("ROLLING_VOLATILITY", delivery_id))
                  for name in branches}
        reference = values["clean"]
        damaged = values["damaged"]
        replayed = values["repaired"]
        affected = damaged is None or (damaged["status"], damaged["numeric_value"]) != (
            replayed["status"], replayed["numeric_value"])
        rows.append({"delivery_id": delivery_id,
                     "window_start_ns": reference["window_start_ns"],
                     "window_end_ns": reference["window_end_ns"],
                     "clean_status": reference["status"], "clean_value": reference["numeric_value"],
                     "damaged_status": damaged["status"] if damaged else "MISSING",
                     "damaged_value": damaged["numeric_value"] if damaged else None,
                     "recovered_status": replayed["status"],
                     "recovered_value": replayed["numeric_value"],
                     "is_affected": affected,
                     "explanation": "Recomputed in controlled fixture replay" if affected else "Unaffected; same result",
                     "revision": None})
    return {"comparison": rows, "metric": "ROLLING_VOLATILITY",
            "revision_note": "Branch comparison only; versioned result revisions are not implemented."}


def run_server(port: int = 8080):
    with socketserver.TCPServer(("127.0.0.1", port), MarketTraceHandler) as httpd:
        print(f"[SERVER] Synthetic investigation dashboard: http://127.0.0.1:{port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
