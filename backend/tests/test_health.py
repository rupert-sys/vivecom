import sentry_sdk
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_endpoint_exposes_prometheus_format():
    """F1-36: /metrics en formato Prometheus/OpenMetrics, para Grafana o Datadog."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "# HELP" in response.text
    assert "# TYPE" in response.text


def test_sentry_is_inert_without_a_dsn():
    """F1-36: sin sentry_dsn configurado (el default de desarrollo), el SDK no debe mandar nada a ningún lado."""
    assert sentry_sdk.get_client().is_active() is False


def test_cors_allows_the_configured_frontend_origin():
    """F1-18: el panel admin (React, otro origen) necesita CORS habilitado para llamar a esta API."""
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_an_origin_not_in_the_allowlist():
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_openapi_schema_is_complete_and_has_no_duplicate_operation_ids():
    """F1-38: Swagger/OpenAPI de todos los endpoints del MVP."""
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"]
    assert schema["info"]["version"]
    assert len(schema["paths"]) > 30  # cubre todos los routers ya montados

    operation_ids = [
        op["operationId"]
        for methods in schema["paths"].values()
        for op in methods.values()
        if isinstance(op, dict) and "operationId" in op
    ]
    assert len(operation_ids) == len(set(operation_ids))
