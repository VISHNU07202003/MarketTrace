"""
MarketTrace Local Offline Warehouse Runner (SQLite-based).
Emulates Snowflake batch staging, ingestion checks, and SQL-based historical metrics.
Guarantees full offline testability without cloud credentials.
"""

import sqlite3
import json
import math
import os
from typing import Dict, Any, List, Optional, Tuple


class LocalWarehouse:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS run_manifests (
            run_id TEXT PRIMARY KEY,
            seed INTEGER,
            input_hash TEXT,
            fault_manifest_hash TEXT,
            calculation_version TEXT,
            status TEXT,
            created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS raw_deliveries (
            run_id TEXT NOT NULL,
            delivery_id TEXT PRIMARY KEY,
            source TEXT,
            source_session TEXT,
            instrument TEXT,
            message_kind TEXT,
            provider_sequence INTEGER,
            receive_time_ns INTEGER NOT NULL,
            replay_time_ns INTEGER NOT NULL,
            side TEXT,
            price_ticks INTEGER,
            size_units INTEGER,
            payload_hash TEXT
        );

        CREATE TABLE IF NOT EXISTS processing_decisions (
            delivery_id TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            reason TEXT,
            decision_time_ns INTEGER NOT NULL,
            resulting_book_state TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS book_checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            delivery_id TEXT NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            best_bid_ticks INTEGER,
            best_ask_ticks INTEGER,
            midpoint_ticks INTEGER,
            spread_ticks INTEGER,
            is_crossed INTEGER,
            is_empty INTEGER,
            book_state TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analytical_results (
            result_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            window_start_ns INTEGER,
            window_end_ns INTEGER,
            revision INTEGER DEFAULT 1,
            status TEXT NOT NULL,
            numeric_value REAL,
            evidence_deliveries TEXT,
            calculation_version TEXT
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            delivery_id TEXT NOT NULL,
            fault_type TEXT NOT NULL,
            detected_at_ns INTEGER NOT NULL,
            status TEXT NOT NULL,
            details TEXT
        );
        """)
        self.conn.commit()

    def load_evidence(self, deliveries_jsonl_path: str, decisions_jsonl_path: str) -> Dict[str, int]:
        """Loads append-only evidence files into raw_deliveries and processing_decisions."""
        cur = self.conn.cursor()
        deliveries_count = 0
        decisions_count = 0

        with open(deliveries_jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                cur.execute("""
                INSERT OR REPLACE INTO raw_deliveries (
                    run_id, delivery_id, source, source_session, instrument,
                    message_kind, provider_sequence, receive_time_ns, replay_time_ns,
                    side, price_ticks, size_units, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d.get("run_id"), d.get("delivery_id"), d.get("source"), d.get("source_session"),
                    d.get("instrument"), d.get("message_kind"), d.get("provider_sequence"),
                    d.get("receive_time_ns"), d.get("replay_time_ns"), d.get("side"),
                    d.get("price_ticks"), d.get("size_units"), d.get("payload_hash")
                ))
                deliveries_count += 1

        with open(decisions_jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                p = json.loads(line)
                cur.execute("""
                INSERT OR REPLACE INTO processing_decisions (
                    delivery_id, code, reason, decision_time_ns, resulting_book_state
                ) VALUES (?, ?, ?, ?, ?)
                """, (
                    p.get("delivery_id"), p.get("code"), p.get("reason"),
                    p.get("decision_time_ns"), p.get("resulting_book_state")
                ))
                decisions_count += 1

        self.conn.commit()
        return {"deliveries": deliveries_count, "decisions": decisions_count}

    def populate_checkpoints_from_metrics(self, run_id: str, expected_metrics_json_path: str) -> int:
        """Populates book_checkpoints from canonical replay output."""
        with open(expected_metrics_json_path, "r") as f:
            records = json.load(f)

        cur = self.conn.cursor()
        count = 0
        for idx, item in enumerate(records):
            del_id = item["delivery_id"]
            dec = item["decision"]
            met = item["metrics"]

            cur.execute("""
            INSERT OR REPLACE INTO book_checkpoints (
                checkpoint_id, run_id, delivery_id, timestamp_ns,
                best_bid_ticks, best_ask_ticks, midpoint_ticks, spread_ticks,
                is_crossed, is_empty, book_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"chk_{idx:04d}_{del_id}",
                run_id,
                del_id,
                dec.get("decision_time_ns", 0),
                met.get("best_bid_ticks"),
                met.get("best_ask_ticks"),
                met.get("midpoint_ticks"),
                met.get("spread_ticks"),
                1 if met.get("is_crossed") else 0,
                1 if met.get("is_empty") else 0,
                dec.get("resulting_book_state", "VALID")
            ))
            count += 1

        self.conn.commit()
        return count

    def compute_analytical_results(self, run_id: str) -> int:
        """
        Computes historical analytical results (midpoints, spreads, rolling volatility)
        and stores them versioned in analytical_results.
        """
        cur = self.conn.cursor()
        
        # 1. Fetch checkpoints
        cur.execute("""
        SELECT checkpoint_id, delivery_id, timestamp_ns, midpoint_ticks, spread_ticks, book_state
        FROM book_checkpoints
        WHERE run_id = ?
        ORDER BY timestamp_ns ASC
        """, (run_id,))
        checkpoints = cur.fetchall()

        results_inserted = 0

        # Store Midpoints and Spreads
        for chk in checkpoints:
            del_id = chk["delivery_id"]
            ts = chk["timestamp_ns"]
            mid = chk["midpoint_ticks"]
            spr = chk["spread_ticks"]
            state = chk["book_state"]

            # Midpoint result
            cur.execute("""
            INSERT OR REPLACE INTO analytical_results (
                result_id, run_id, metric_name, window_start_ns, window_end_ns,
                revision, status, numeric_value, evidence_deliveries, calculation_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"res_mid_{del_id}", run_id, "MIDPOINT", ts, ts, 1,
                state, float(mid) if mid is not None else None,
                del_id, "v1.0"
            ))
            results_inserted += 1

            # Spread result
            cur.execute("""
            INSERT OR REPLACE INTO analytical_results (
                result_id, run_id, metric_name, window_start_ns, window_end_ns,
                revision, status, numeric_value, evidence_deliveries, calculation_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"res_spr_{del_id}", run_id, "SPREAD", ts, ts, 1,
                state, float(spr) if spr is not None else None,
                del_id, "v1.0"
            ))
            results_inserted += 1

        # 2. Rolling Volatility over 11 valid observations (10 returns)
        # Window slides over valid midpoints
        valid_points = [chk for chk in checkpoints if chk["book_state"] == "VALID" and chk["midpoint_ticks"] is not None]

        for i in range(len(checkpoints)):
            current_chk = checkpoints[i]
            # Window of 11 consecutive points up to index i
            if i < 10:
                # Incomplete initial window
                window_chk = checkpoints[0 : i + 1]
                cur.execute("""
                INSERT OR REPLACE INTO analytical_results (
                    result_id, run_id, metric_name, window_start_ns, window_end_ns,
                    revision, status, numeric_value, evidence_deliveries, calculation_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"res_vol_{current_chk['delivery_id']}", run_id, "ROLLING_VOLATILITY",
                    window_chk[0]["timestamp_ns"], current_chk["timestamp_ns"], 1,
                    "INCOMPLETE", None,
                    ",".join(c["delivery_id"] for c in window_chk), "v1.0"
                ))
                results_inserted += 1
            else:
                window_chk = checkpoints[i - 10 : i + 1]
                # Check if all 11 in this window are VALID
                any_corrupted = any(c["book_state"] != "VALID" or c["midpoint_ticks"] is None for c in window_chk)
                
                if any_corrupted:
                    status = "INCOMPLETE"
                    vol = None
                else:
                    midpoints = [float(c["midpoint_ticks"]) for c in window_chk]
                    # Calculate sample standard deviation
                    returns = [math.log(midpoints[k] / midpoints[k - 1]) for k in range(1, 11)]
                    mean_r = sum(returns) / 10.0
                    var_r = sum((r - mean_r) ** 2 for r in returns) / 9.0
                    vol = math.sqrt(var_r)
                    status = "VALID"

                cur.execute("""
                INSERT OR REPLACE INTO analytical_results (
                    result_id, run_id, metric_name, window_start_ns, window_end_ns,
                    revision, status, numeric_value, evidence_deliveries, calculation_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"res_vol_{current_chk['delivery_id']}", run_id, "ROLLING_VOLATILITY",
                    window_chk[0]["timestamp_ns"], current_chk["timestamp_ns"], 1,
                    status, vol,
                    ",".join(c["delivery_id"] for c in window_chk), "v1.0"
                ))
                results_inserted += 1

        self.conn.commit()
        return results_inserted

    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM raw_deliveries WHERE run_id = ?", (run_id,))
        total_del = cur.fetchone()["total"]

        cur.execute("""
        SELECT p.code, COUNT(*) AS count
        FROM processing_decisions p
        JOIN raw_deliveries d ON p.delivery_id = d.delivery_id
        WHERE d.run_id = ?
        GROUP BY p.code
        """, (run_id,))
        decisions_by_code = {row["code"]: row["count"] for row in cur.fetchall()}

        cur.execute("""
        SELECT metric_name, status, COUNT(*) AS count
        FROM analytical_results
        WHERE run_id = ?
        GROUP BY metric_name, status
        """, (run_id,))
        results_summary = {}
        for row in cur.fetchall():
            m = row["metric_name"]
            if m not in results_summary:
                results_summary[m] = {}
            results_summary[m][row["status"]] = row["count"]

        return {
            "run_id": run_id,
            "total_deliveries": total_del,
            "decisions": decisions_by_code,
            "results_summary": results_summary
        }
