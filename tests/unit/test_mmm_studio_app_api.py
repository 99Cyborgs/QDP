from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
APP_SRC = ROOT / "apps" / "mmm_studio" / "src"
PACKAGE_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
for path in [QDP_IO_SRC, APP_SRC, PACKAGE_SRC]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mmm_studio.api import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_leaderboard() -> None:
    client = TestClient(app)
    response = client.get("/leaderboard?top_n=3")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert "genome_id" in payload[0]


def test_scoring_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/scoring/score", json={"profile": "broadband", "top_n": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"] == "broadband"
    assert payload["candidate_count"] >= 2
    assert len(payload["results"]) == 2


def test_registry_validation_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/registry/validate", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"]["mechanisms"] == 11
    assert payload["issues"] == []
