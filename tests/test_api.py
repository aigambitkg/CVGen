"""Tests for the CVGen REST API."""

import pytest

try:
    from fastapi.testclient import TestClient
    from cvgen.api.app import app, backend_registry, _init_backends

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")


@pytest.fixture(autouse=True)
def setup_backends():
    """Initialize backends before each test."""
    _init_backends()
    yield
    backend_registry.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_check(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["backends_available"] >= 1


class TestBackends:
    def test_list_backends(self, client):
        res = client.get("/api/v1/backends")
        assert res.status_code == 200
        data = res.json()
        assert len(data["backends"]) >= 1
        assert data["backends"][0]["name"] == "simulator"

    def test_simulator_available(self, client):
        res = client.get("/api/v1/backends")
        names = [b["name"] for b in res.json()["backends"]]
        assert "simulator" in names


class TestCircuits:
    def test_execute_bell_state(self, client):
        res = client.post("/api/v1/circuits/execute", json={
            "num_qubits": 2,
            "gates": [
                {"gate": "h", "targets": [0]},
                {"gate": "cx", "targets": [0, 1]},
            ],
            "shots": 1000,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["shots"] == 1000
        # Bell state should produce 00 and 11
        assert "00" in data["counts"] or "11" in data["counts"]

    def test_execute_single_qubit(self, client):
        res = client.post("/api/v1/circuits/execute", json={
            "num_qubits": 1,
            "gates": [
                {"gate": "x", "targets": [0]},
            ],
            "shots": 100,
        })
        assert res.status_code == 200
        data = res.json()
        # X gate on |0> should give |1>
        assert data["most_likely"] == "1"

    def test_execute_parametric_gate(self, client):
        import math
        res = client.post("/api/v1/circuits/execute", json={
            "num_qubits": 1,
            "gates": [
                {"gate": "rx", "targets": [0], "params": [math.pi]},
            ],
            "shots": 100,
        })
        assert res.status_code == 200

    def test_invalid_gate(self, client):
        res = client.post("/api/v1/circuits/execute", json={
            "num_qubits": 1,
            "gates": [
                {"gate": "invalid_gate", "targets": [0]},
            ],
            "shots": 100,
        })
        assert res.status_code == 400

    def test_invalid_backend(self, client):
        res = client.post("/api/v1/circuits/execute", json={
            "num_qubits": 1,
            "gates": [{"gate": "h", "targets": [0]}],
            "backend": "nonexistent",
        })
        assert res.status_code == 404


class TestAgents:
    def test_grover_search(self, client):
        res = client.post("/api/v1/agents/grover", json={
            "num_qubits": 2,
            "target_states": [3],
            "shots": 1024,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert 3 in data["solutions"]

    def test_grover_invalid_target(self, client):
        res = client.post("/api/v1/agents/grover", json={
            "num_qubits": 2,
            "target_states": [99],  # Out of range for 2 qubits
            "shots": 100,
        })
        assert res.status_code == 400

    def test_vqe_optimization(self, client):
        res = client.post("/api/v1/agents/vqe", json={
            "num_qubits": 1,
            "cost_observable": {"0": 0.0, "1": 1.0},
            "ansatz_depth": 1,
            "max_iterations": 20,
            "shots": 256,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["optimal_cost"] < 0.5  # Should minimize toward 0


class TestWebUI:
    def test_serve_index(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "CVGen" in res.text
