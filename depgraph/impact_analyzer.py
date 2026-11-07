"""
MarketTrace DepGraph Impact Analyzer.
Evaluates calculation-window dependencies, fault propagation,
honest recovery boundaries, and selective recomputation plans.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from reference.models import QualityState, DecisionCode
from depgraph.registry import NodeKind, DependencyNode, DependencyGraph


class ImpactAnalyzer:
    def __init__(self, instrument: str = "BTC-USD"):
        self.instrument = instrument
        self.graph = DependencyGraph()
        self.delivery_records: List[Dict[str, Any]] = []

    def build_graph_from_records(self, delivery_records: List[Dict[str, Any]]):
        """
        Builds the typed dependency topology from sequential delivery records:
        For each delivery:
          raw_delivery -> order_book -> best_quotes -> midpoint_spread -> log_returns
        And for rolling volatility:
          collects 10 preceding log_returns -> rolling_volatility window.
        """
        self.delivery_records = delivery_records
        self.graph = DependencyGraph()
        g = self.graph

        prev_midpoint_id: Optional[str] = None
        prev_ts: Optional[int] = None
        prev_quality = QualityState.INCOMPLETE
        prev_evidence: Set[str] = set()
        returns_history: List[Tuple[str, int, int]] = []  # node, start timestamp, end timestamp

        for idx, rec in enumerate(delivery_records):
            del_id = rec["delivery_id"]
            ts = rec.get("timestamp_ns", idx * 100_000_000)
            dec_code = rec.get("decision_code", "ACCEPTED")
            initial_state = QualityState(rec.get("book_state", "VALID" if dec_code == "ACCEPTED" else "INCOMPLETE"))

            # 1. Raw Delivery Node
            raw_id = f"raw_{del_id}"
            g.add_node(DependencyNode(
                node_id=raw_id,
                kind=NodeKind.RAW_DELIVERY,
                instrument=self.instrument,
                time_window=(ts, ts),
                quality_state=QualityState.VALID,
                evidence_delivery_ids={del_id},
                explanation="Raw event delivery arrival"
            ))

            # 2. Order Book Node
            book_id = f"book_{del_id}"
            g.add_node(DependencyNode(
                node_id=book_id,
                kind=NodeKind.ORDER_BOOK,
                instrument=self.instrument,
                time_window=(ts, ts),
                quality_state=initial_state,
                evidence_delivery_ids={del_id},
                explanation=f"Order book state after delivery {del_id}"
            ))
            g.add_edge(raw_id, book_id)

            # 3. Best Quotes Node
            quotes_id = f"quotes_{del_id}"
            g.add_node(DependencyNode(
                node_id=quotes_id,
                kind=NodeKind.BEST_QUOTES,
                instrument=self.instrument,
                time_window=(ts, ts),
                quality_state=initial_state,
                evidence_delivery_ids={del_id},
                explanation=f"Best bid and ask quotes for {del_id}"
            ))
            g.add_edge(book_id, quotes_id)

            # 4. Midpoint & Spread Node
            mid_id = f"mid_{del_id}"
            g.add_node(DependencyNode(
                node_id=mid_id,
                kind=NodeKind.MIDPOINT_SPREAD,
                instrument=self.instrument,
                time_window=(ts, ts),
                quality_state=initial_state,
                evidence_delivery_ids={del_id},
                explanation=f"Midpoint and spread calculation for {del_id}"
            ))
            g.add_edge(quotes_id, mid_id)

            # 5. Log Returns Node (requires current midpoint and preceding midpoint)
            ret_id = f"ret_{del_id}"
            if rec.get("message_kind", "UPDATE") == "UPDATE" and prev_midpoint_id is not None:
                valid_return = (initial_state == QualityState.VALID and
                                prev_quality == QualityState.VALID and
                                ts - prev_ts == 1_000_000_000)
                g.add_node(DependencyNode(
                    node_id=ret_id,
                    kind=NodeKind.LOG_RETURNS,
                    instrument=self.instrument,
                    time_window=(prev_ts, ts),
                    quality_state=QualityState.VALID if valid_return else QualityState.INCOMPLETE,
                    evidence_delivery_ids=prev_evidence | {del_id},
                    explanation=f"Log return between {prev_midpoint_id} and {mid_id}"
                ))
                g.add_edge(prev_midpoint_id, ret_id)
                g.add_edge(mid_id, ret_id)
                returns_history.append((ret_id, prev_ts, ts))
            if rec.get("message_kind", "UPDATE") == "UPDATE":
                prev_midpoint_id = mid_id
                prev_ts = ts
                prev_quality = initial_state
                prev_evidence = {del_id}

            # 6. Rolling Volatility Node (requires 10 consecutive log returns)
            vol_id = f"vol_{del_id}"
            if rec.get("message_kind", "UPDATE") == "UPDATE" and len(returns_history) >= 10:
                window_returns = returns_history[-10:]
                start_window_ts = window_returns[0][1]
                end_window_ts = window_returns[-1][2]
                window_evidence = set().union(*(g.nodes[r[0]].evidence_delivery_ids for r in window_returns))
                valid_window = all(g.nodes[r[0]].quality_state == QualityState.VALID for r in window_returns)

                g.add_node(DependencyNode(
                    node_id=vol_id,
                    kind=NodeKind.ROLLING_VOLATILITY,
                    instrument=self.instrument,
                    time_window=(start_window_ts, end_window_ts),
                    quality_state=QualityState.VALID if valid_window else QualityState.INCOMPLETE,
                    evidence_delivery_ids=window_evidence,
                    explanation=f"10-period rolling volatility ending at {del_id}"
                ))
                for ret_node_id, _, _ in window_returns:
                    g.add_edge(ret_node_id, vol_id)

    def propagate_invalidation(self, failed_delivery_id: str, reason: str) -> Tuple[Set[str], Set[str]]:
        """
        Invalidates order book at failed_delivery_id and cascades downstream.
        Returns:
            affected_node_ids: nodes invalidated by the failure
            unaffected_node_ids: nodes that remain VALID
        """
        book_id = f"book_{failed_delivery_id}"
        if book_id not in self.graph.nodes:
            raise KeyError(f"Node {book_id} not in graph")

        # Mark source node as INCOMPLETE
        self.graph.nodes[book_id].quality_state = QualityState.INCOMPLETE
        self.graph.nodes[book_id].explanation = f"Direct fault at delivery {failed_delivery_id}: {reason}"

        # Find all downstream consumers
        descendants = self.graph.get_descendants(book_id)
        for nid in descendants:
            node = self.graph.nodes[nid]
            node.quality_state = QualityState.INCOMPLETE
            node.explanation = f"Invalidated by upstream failure at {failed_delivery_id}"

        affected = descendants | {book_id}
        unaffected = {nid for nid, n in self.graph.nodes.items() if n.quality_state == QualityState.VALID}

        return affected, unaffected

    def apply_resync_snapshot(self, resync_delivery_id: str):
        """
        Applies authoritative snapshot resync:
        - Restores current book and subsequent quotes to VALID.
        - DOES NOT heal historical windows that required missing historical deliveries.
        """
        source = next((rec for rec in self.delivery_records
                       if rec["delivery_id"] == resync_delivery_id), None)
        if (source is None or source.get("message_kind") != "SNAPSHOT" or
                source.get("book_state") != "VALID" or
                source.get("decision_code") != "ACCEPTED"):
            raise ValueError("Resync requires an accepted complete valid snapshot")
        book_id = f"book_{resync_delivery_id}"
        if book_id in self.graph.nodes:
            self.graph.nodes[book_id].quality_state = QualityState.VALID
            self.graph.nodes[book_id].explanation = "Restored by fresh authoritative snapshot"

        quotes_id = f"quotes_{resync_delivery_id}"
        if quotes_id in self.graph.nodes:
            self.graph.nodes[quotes_id].quality_state = QualityState.VALID
            self.graph.nodes[quotes_id].explanation = "Valid quotes restored by fresh snapshot"

        mid_id = f"mid_{resync_delivery_id}"
        if mid_id in self.graph.nodes:
            self.graph.nodes[mid_id].quality_state = QualityState.VALID

    def plan_recomputation(self, restored_delivery_ids: Set[str]) -> List[str]:
        """
        Given a set of restored historical deliveries (e.g., from controlled fixture recovery),
        identifies the exact topologically ordered recomputation plan.
        Only nodes requiring the restored evidence are included.
        """
        affected_roots = {f"book_{del_id}" for del_id in restored_delivery_ids if f"book_{del_id}" in self.graph.nodes}
        recompute_nodes: Set[str] = set()

        for root in affected_roots:
            recompute_nodes.add(root)
            recompute_nodes.update(self.graph.get_descendants(root))

        # Topologically sort the entire graph and filter for recompute_nodes
        full_order = self.graph.get_topological_sort()
        plan = [nid for nid in full_order if nid in recompute_nodes]

        # A plan alone cannot certify new values or create a persisted revision.
        return plan
