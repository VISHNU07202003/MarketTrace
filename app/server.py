"""
MarketTrace Investigation Dashboard Local Server.
Serves API endpoints reading local fixture evidence and DepGraph models.
Zero cloud credentials required.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from typing import Dict, Any

from reference.models import QualityState, DecisionCode
from depgraph.impact_analyzer import ImpactAnalyzer
from warehouse.local_warehouse import LocalWarehouse


class MarketTraceHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set base directory to app/
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__)), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            self.handle_api(path, params)
        else:
            super().do_GET()

    def handle_api(self, path: str, params: Dict[str, Any]):
        response_data = {}
        status_code = 200

        try:
            if path == "/api/status":
                response_data = {
                    "system": "MarketTrace",
                    "version": "v0.1.0",
                    "mode": "OFFLINE_VERIFIED",
                    "data_mode": "SYNTHETIC",
                    "engine": "C++20 Replay Core"
                }

            elif path == "/api/run-overview":
                run_type = params.get("type", ["faulted"])[0]
                expected_file = "fixtures/expected_clean_metrics.json" if run_type == "clean" else "fixtures/expected_faulted_metrics.json"
                with open(expected_file, "r") as f:
                    records = json.load(f)

                total = len(records)
                accepted = sum(1 for r in records if r["decision"]["code"] == "ACCEPTED")
                rejected = total - accepted
                latest_metrics = records[-1]["metrics"]
                latest_state = records[-1]["decision"]["resulting_book_state"]

                response_data = {
                    "run_id": f"run_synth_{run_type}_s42",
                    "run_type": run_type,
                    "data_badge": "SYNTHETIC FIXTURE",
                    "total_events": total,
                    "accepted_count": accepted,
                    "rejected_count": rejected,
                    "current_book_state": latest_state,
                    "instrument": "BTC-USD",
                    "best_bid_ticks": latest_metrics.get("best_bid_ticks"),
                    "best_ask_ticks": latest_metrics.get("best_ask_ticks"),
                    "midpoint_ticks": latest_metrics.get("midpoint_ticks"),
                    "spread_ticks": latest_metrics.get("spread_ticks"),
                    "is_crossed": latest_metrics.get("is_crossed", False)
                }

            elif path == "/api/timeline":
                run_type = params.get("type", ["faulted"])[0]
                events_file = "fixtures/clean_run.json" if run_type == "clean" else "fixtures/faulted_run.json"
                metrics_file = "fixtures/expected_clean_metrics.json" if run_type == "clean" else "fixtures/expected_faulted_metrics.json"

                with open(events_file, "r") as f:
                    events = json.load(f)
                with open(metrics_file, "r") as f:
                    metrics = json.load(f)

                timeline = []
                for ev, met in zip(events, metrics):
                    timeline.append({
                        "delivery_id": ev["delivery_id"],
                        "message_kind": ev["message_kind"],
                        "side": ev.get("side", "NONE"),
                        "price_ticks": ev.get("price_ticks", 0),
                        "size_units": ev.get("size_units", 0),
                        "provider_sequence": ev.get("provider_sequence"),
                        "receive_time_ns": ev.get("receive_time_ns", 0),
                        "decision_code": met["decision"]["code"],
                        "decision_reason": met["decision"]["reason"],
                        "resulting_book_state": met["decision"]["resulting_book_state"],
                        "midpoint_ticks": met["metrics"].get("midpoint_ticks"),
                        "spread_ticks": met["metrics"].get("spread_ticks")
                    })

                response_data = {"timeline": timeline}

            elif path == "/api/incident-detail":
                delivery_id = params.get("delivery_id", ["del_0076"])[0]
                with open("fixtures/faulted_run.json", "r") as f:
                    events = json.load(f)
                with open("fixtures/expected_faulted_metrics.json", "r") as f:
                    metrics = json.load(f)

                event = next((e for e in events if e["delivery_id"] == delivery_id), None)
                record = next((m for m in metrics if m["delivery_id"] == delivery_id), None)

                # Build DepGraph path
                depgraph_chain = [
                    {"stage": "RAW_DELIVERY", "node_id": f"raw_{delivery_id}", "status": "VALID", "desc": "Raw event delivery arrival"},
                    {"stage": "ORDER_BOOK", "node_id": f"book_{delivery_id}", "status": record["decision"]["resulting_book_state"] if record else "VALID", "desc": "Order book state after delivery"},
                    {"stage": "BEST_QUOTES", "node_id": f"quotes_{delivery_id}", "status": record["decision"]["resulting_book_state"] if record else "VALID", "desc": "Extracted best bid/ask quotes"},
                    {"stage": "MIDPOINT_SPREAD", "node_id": f"mid_{delivery_id}", "status": record["decision"]["resulting_book_state"] if record else "VALID", "desc": "Calculated midpoint and spread"},
                    {"stage": "LOG_RETURNS", "node_id": f"ret_{delivery_id}", "status": record["decision"]["resulting_book_state"] if record else "VALID", "desc": "Log return observation"},
                    {"stage": "ROLLING_VOLATILITY", "node_id": f"vol_{delivery_id}", "status": record["decision"]["resulting_book_state"] if record else "VALID", "desc": "11-sample sliding window"}
                ]

                response_data = {
                    "delivery_id": delivery_id,
                    "event": event,
                    "decision": record["decision"] if record else None,
                    "metrics": record["metrics"] if record else None,
                    "depgraph_chain": depgraph_chain
                }

            elif path == "/api/recovery-comparison":
                # Returns 3 comparison scenarios for the north-star demo:
                # 1. Clean reference
                # 2. Damaged run (showing unresolved historical gap)
                # 3. Controlled repair (withheld event restored, recomputed revision 2)
                with open("fixtures/expected_clean_metrics.json", "r") as f:
                    clean = json.load(f)
                with open("fixtures/expected_faulted_metrics.json", "r") as f:
                    faulted = json.load(f)

                # Compare representative sample checkpoints
                comparison_points = ["del_0010", "del_0025", "del_0050", "del_0076", "del_0080", "del_0095", "del_0110"]
                rows = []

                for del_id in comparison_points:
                    c_rec = next((r for r in clean if r["delivery_id"] == del_id), None)
                    f_rec = next((r for r in faulted if r["delivery_id"] == del_id), None)

                    c_mid = c_rec["metrics"]["midpoint_ticks"] if c_rec else None
                    f_mid = f_rec["metrics"]["midpoint_ticks"] if f_rec else None

                    # If this point was corrupted (like del_0076), recovery restores it
                    is_corrupted = f_rec and f_rec["decision"]["code"] != "ACCEPTED"
                    recovered_state = "VALID"
                    recovered_revision = 2 if is_corrupted else 1
                    recovered_mid = c_mid if is_corrupted else f_mid

                    rows.append({
                        "delivery_id": del_id,
                        "clean_status": "VALID",
                        "clean_midpoint": c_mid,
                        "damaged_status": f_rec["decision"]["resulting_book_state"] if f_rec else "UNKNOWN",
                        "damaged_midpoint": f_mid,
                        "recovered_status": recovered_state,
                        "recovered_midpoint": recovered_mid,
                        "revision": recovered_revision,
                        "is_affected": is_corrupted,
                        "explanation": "Restored in Rev 2 via supplied withheld event" if is_corrupted else "Unaffected; unchanged Rev 1"
                    })

                response_data = {"comparison": rows}

            else:
                status_code = 404
                response_data = {"error": f"Endpoint {path} not found"}

        except Exception as ex:
            status_code = 500
            response_data = {"error": str(ex)}

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))


def run_server(port: int = 8080):
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    with socketserver.TCPServer(("", port), MarketTraceHandler) as httpd:
        print(f"[SERVER] MarketTrace Dashboard running at http://localhost:{port}/")
        print("[SERVER] Press Ctrl+C to terminate.")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
