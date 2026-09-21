from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_minimal_liveness_payload(monkeypatch):
    monkeypatch.delenv("MNEMOSYNE_VERSION", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mnemosyne-visual-monitor",
        "version": None,
    }


def test_health_reports_configured_version(monkeypatch):
    monkeypatch.setenv("MNEMOSYNE_VERSION", "18.0.0-test")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mnemosyne-visual-monitor",
        "version": "18.0.0-test",
    }
