import pytest
from reference.models import QualityState
from depgraph.registry import NodeKind, DependencyNode, DependencyGraph
from depgraph.impact_analyzer import ImpactAnalyzer


def test_dependency_graph_topology_and_cycle_rejection():
    g = DependencyGraph()
    n1 = DependencyNode("n1", NodeKind.RAW_DELIVERY)
    n2 = DependencyNode("n2", NodeKind.ORDER_BOOK)
    n3 = DependencyNode("n3", NodeKind.BEST_QUOTES)

    g.add_node(n1)
    g.add_node(n2)
    g.add_node(n3)

    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")

    order = g.get_topological_sort()
    assert order == ["n1", "n2", "n3"]

    # Introduce cycle: n3 -> n1
    g.add_edge("n3", "n1")
    with pytest.raises(ValueError, match="cycle detected"):
        g.get_topological_sort()


def test_impact_analysis_and_unaffected_set():
    analyzer = ImpactAnalyzer("BTC-USD")

    # Create 30 sequential delivery records
    records = []
    for i in range(1, 31):
        records.append({
            "delivery_id": f"del_{i:04d}",
            "timestamp_ns": i * 100_000_000,
            "decision_code": "ACCEPTED"
        })

    analyzer.build_graph_from_records(records)
    assert len(analyzer.graph.nodes) > 100

    # Invalidate delivery del_0015
    affected, unaffected = analyzer.propagate_invalidation("del_0015", "Sequence gap detected")

    assert "book_del_0015" in affected
    assert "quotes_del_0015" in affected
    assert "mid_del_0015" in affected
    assert "ret_del_0015" in affected

    # Nodes before del_0015 must remain completely unaffected (VALID)
    assert "book_del_0005" in unaffected
    assert "quotes_del_0005" in unaffected
    assert "mid_del_0005" in unaffected
    assert analyzer.graph.nodes["book_del_0005"].quality_state == QualityState.VALID


def test_honest_recovery_and_controlled_recomputation():
    analyzer = ImpactAnalyzer("BTC-USD")

    records = []
    for i in range(1, 31):
        records.append({
            "delivery_id": f"del_{i:04d}",
            "timestamp_ns": i * 100_000_000,
            "decision_code": "ACCEPTED"
        })

    analyzer.build_graph_from_records(records)

    # Invalidate delivery del_0015 (sequence gap)
    affected, _ = analyzer.propagate_invalidation("del_0015", "Sequence gap")

    # Verify that a rolling volatility window covering del_0015 is INCOMPLETE
    vol_nodes_affected = [nid for nid in affected if nid.startswith("vol_")]
    assert len(vol_nodes_affected) > 0
    for v in vol_nodes_affected:
        assert analyzer.graph.nodes[v].quality_state == QualityState.INCOMPLETE

    # 1. Honest Recovery via fresh snapshot at del_0025
    analyzer.apply_resync_snapshot("del_0025")
    # Current book at del_0025 is now VALID
    assert analyzer.graph.nodes["book_del_0025"].quality_state == QualityState.VALID
    assert analyzer.graph.nodes["quotes_del_0025"].quality_state == QualityState.VALID
    
    # BUT older historical volatility windows covering del_0015 STILL REMAIN INCOMPLETE!
    for v in vol_nodes_affected:
        assert analyzer.graph.nodes[v].quality_state == QualityState.INCOMPLETE
        assert analyzer.graph.nodes[v].revision == 1

    # 2. Controlled Recomputation: restore the missing authoritative event del_0015
    plan = analyzer.plan_recomputation({"del_0015"})
    assert len(plan) > 0
    assert "book_del_0015" in plan

    # After controlled recomputation:
    # All recomputed nodes transition to VALID and revision 2
    for nid in plan:
        assert analyzer.graph.nodes[nid].quality_state == QualityState.VALID
        assert analyzer.graph.nodes[nid].revision == 2

    # Unaffected prior nodes remain at revision 1
    assert analyzer.graph.nodes["book_del_0005"].revision == 1
    assert analyzer.graph.nodes["book_del_0005"].quality_state == QualityState.VALID
