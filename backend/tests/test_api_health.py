from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_global_health_and_openapi_available() -> None:
    client = TestClient(create_app())

    health_resp = client.get("/healthz")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200


def test_module_health_routes_available() -> None:
    client = TestClient(create_app())
    module_paths = [
        "/api/v1/auth/health",
        "/api/v1/leads/health",
        "/api/v1/crm/health",
        "/api/v1/content/health",
        "/api/v1/kb/health",
        "/api/v1/metrics/health",
        "/api/v1/audit/health",
    ]

    for path in module_paths:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

