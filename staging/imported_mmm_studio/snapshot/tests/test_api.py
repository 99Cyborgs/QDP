from fastapi.testclient import TestClient

from mmm_studio.api import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_leaderboard():
    client = TestClient(app)
    response = client.get("/leaderboard?top_n=3")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert "genome_id" in payload[0]


def test_scoring_endpoint():
    client = TestClient(app)
    response = client.post("/scoring/score", json={"profile": "broadband", "top_n": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"] == "broadband"
    assert payload["candidate_count"] >= 2
    assert len(payload["results"]) == 2


def test_registry_validation_endpoint():
    client = TestClient(app)
    response = client.post("/registry/validate", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"]["mechanisms"] == 11
    assert payload["issues"] == []
