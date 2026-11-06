"""
MarketTrace DepGraph Dependency Registry.
Extends the dependency graph paradigm to typed temporal calculation windows:
RawDelivery -> OrderBook -> BestQuotes -> MidpointSpread -> LogReturns -> RollingVolatility.
"""

from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any
from reference.models import QualityState


class NodeKind(str, Enum):
    RAW_DELIVERY = "RAW_DELIVERY"
    ORDER_BOOK = "ORDER_BOOK"
    BEST_QUOTES = "BEST_QUOTES"
    MIDPOINT_SPREAD = "MIDPOINT_SPREAD"
    LOG_RETURNS = "LOG_RETURNS"
    ROLLING_VOLATILITY = "ROLLING_VOLATILITY"


class DependencyNode:
    def __init__(
        self,
        node_id: str,
        kind: NodeKind,
        instrument: str = "BTC-USD",
        time_window: Tuple[int, int] = (0, 0),
        quality_state: QualityState = QualityState.VALID,
        evidence_delivery_ids: Optional[Set[str]] = None,
        calculation_version: str = "v1.0",
        revision: int = 1,
        explanation: str = "Initialized"
    ):
        self.node_id = node_id
        self.kind = kind
        self.instrument = instrument
        self.time_window = time_window  # (start_ns, end_ns)
        self.quality_state = quality_state
        self.evidence_delivery_ids = evidence_delivery_ids or set()
        self.calculation_version = calculation_version
        self.revision = revision
        self.explanation = explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind.value,
            "instrument": self.instrument,
            "time_window": list(self.time_window),
            "quality_state": self.quality_state.value,
            "evidence_delivery_ids": sorted(list(self.evidence_delivery_ids)),
            "calculation_version": self.calculation_version,
            "revision": self.revision,
            "explanation": self.explanation
        }


class DependencyGraph:
    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}
        # Adjacency list: producer_id -> set of consumer_ids
        self.adjacency: Dict[str, Set[str]] = {}
        # Reverse adjacency: consumer_id -> set of producer_ids
        self.predecessors: Dict[str, Set[str]] = {}

    def add_node(self, node: DependencyNode):
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = set()
        if node.node_id not in self.predecessors:
            self.predecessors[node.node_id] = set()

    def add_edge(self, producer_id: str, consumer_id: str):
        if producer_id not in self.nodes:
            raise KeyError(f"Producer node not found: {producer_id}")
        if consumer_id not in self.nodes:
            raise KeyError(f"Consumer node not found: {consumer_id}")

        self.adjacency[producer_id].add(consumer_id)
        self.predecessors[consumer_id].add(producer_id)

    def get_topological_sort(self) -> List[str]:
        """
        Returns a topologically sorted list of node IDs.
        Detects and rejects cycles with a clear error.
        """
        in_degree = {nid: len(self.predecessors[nid]) for nid in self.nodes}
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes = []

        while queue:
            curr = queue.pop(0)
            sorted_nodes.append(curr)

            for neighbor in self.adjacency[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(self.nodes):
            raise ValueError("Dependency cycle detected in DepGraph! Rejecting invalid computation topology.")

        return sorted_nodes

    def get_descendants(self, root_id: str) -> Set[str]:
        """Returns all transitive downstream consumers of root_id."""
        visited: Set[str] = set()
        stack = [root_id]
        while stack:
            curr = stack.pop()
            for child in self.adjacency.get(curr, set()):
                if child not in visited:
                    visited.add(child)
                    stack.append(child)
        return visited
