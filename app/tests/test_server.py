import json
import socketserver
import threading
import urllib.error
import urllib.request

import pytest

from app.server import MarketTraceHandler


@pytest.fixture(scope="module")
def local_server():
    with socketserver.TCPServer(("127.0.0.1", 0), MarketTraceHandler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()
        thread.join(timeout=5)


def get(base, endpoint):
    with urllib.request.urlopen(base + endpoint, timeout=5) as res:
        assert res.status == 200
        return json.load(res)


def test_offline_status_and_invalid_branch(local_server):
    status = get(local_server, "/api/status")
    assert status["mode"] == "OFFLINE SYNTHETIC"
    assert status["cloud_status"] == "SNOWFLAKE NOT VERIFIED"
    with pytest.raises(urllib.error.HTTPError) as error:
        get(local_server, "/api/timeline?type=../../etc")
    assert error.value.code == 400


def test_overview_and_missing_event(local_server):
    damaged = get(local_server, "/api/run-overview?type=damaged")
    clean = get(local_server, "/api/run-overview?type=clean")
    assert (damaged["total_events"], clean["total_events"]) == (104, 105)
    assert damaged["current_book_state"] == "VALID"
    assert damaged["record_source"] in ("PYTHON REFERENCE", "C++ ENGINE")
    timeline = get(local_server, "/api/timeline?type=damaged")["timeline"]
    assert "inc_0060" not in {e["delivery_id"] for e in timeline}
    assert next(e for e in timeline if e["delivery_id"] == "inc_0061")["decision_code"] == "REJECTED_OUT_OF_SEQUENCE"


def test_incident_lineage_has_measured_quality(local_server):
    detail = get(local_server, "/api/incident-detail?delivery_id=inc_0061")
    assert detail["decision"]["resulting_book_state"] == "INCOMPLETE"
    assert detail["injected_fault_info"]["fault_type"] == "SEQUENCE_GAP"
    assert detail["nearest_snapshot"]["delivery_id"] == "inc_ask_0"
    assert detail["volatility_result"]["status"] == "INCOMPLETE"
    assert detail["volatility_result"]["numeric_value"] is None
    assert [node["stage"] for node in detail["depgraph_chain"]][:2] == ["RAW_DELIVERY", "ORDER_BOOK"]
    later = get(local_server, "/api/incident-detail?delivery_id=inc_0091")
    assert later["nearest_snapshot"]["delivery_id"] == "inc_resync_ask"
    assert later["volatility_result"]["status"] == "VALID"


def test_comparison_uses_recomputed_branches_without_fake_revisions(local_server):
    response = get(local_server, "/api/recovery-comparison")
    by_id = {row["delivery_id"]: row for row in response["comparison"]}
    assert by_id["inc_0060"]["damaged_status"] == "MISSING"
    assert by_id["inc_0061"]["damaged_status"] == "INCOMPLETE"
    assert by_id["inc_0061"]["recovered_status"] == "VALID"
    assert by_id["inc_0061"]["is_affected"]
    assert not by_id["inc_0059"]["is_affected"]
    assert not by_id["inc_0091"]["is_affected"]
    assert all(row["revision"] is None for row in by_id.values())
