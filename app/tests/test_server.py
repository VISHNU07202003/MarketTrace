import pytest
import threading
import time
import urllib.request
import json
import socket
from app.server import MarketTraceHandler
import socketserver


def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def local_server():
    port = get_free_port()
    httpd = socketserver.TCPServer(("", port), MarketTraceHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    httpd.shutdown()


def test_api_status(local_server):
    with urllib.request.urlopen(f"{local_server}/api/status") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["system"] == "MarketTrace"
        assert data["mode"] == "OFFLINE_VERIFIED"


def test_api_run_overview(local_server):
    with urllib.request.urlopen(f"{local_server}/api/run-overview?type=faulted") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["total_events"] == 113
        assert data["accepted_count"] == 106
        assert data["current_book_state"] == "VALID"


def test_api_timeline(local_server):
    with urllib.request.urlopen(f"{local_server}/api/timeline?type=faulted") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert len(data["timeline"]) == 113


def test_api_incident_detail(local_server):
    with urllib.request.urlopen(f"{local_server}/api/incident-detail?delivery_id=del_0076") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["delivery_id"] == "del_0076"
        assert data["decision"]["code"] == "REJECTED_OUT_OF_SEQUENCE"
        assert len(data["depgraph_chain"]) == 6


def test_api_recovery_comparison(local_server):
    with urllib.request.urlopen(f"{local_server}/api/recovery-comparison") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert len(data["comparison"]) > 0
        del_76 = next(c for c in data["comparison"] if c["delivery_id"] == "del_0076")
        assert del_76["is_affected"] is True
        assert del_76["revision"] == 2
