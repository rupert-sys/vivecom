import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from unittest.mock import patch

from app.core.config import settings
from app.core.database import control_session
from app.main import app
from app.services import deposit_processing_service as dps


def _signed_request(client, body: dict, secret: str = None):
    secret = secret or settings.stp_webhook_secret
    raw = json.dumps(body).encode()
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post(
        "/payments/webhook/stp",
        content=raw,
        headers={"X-STP-Signature": signature, "Content-Type": "application/json"},
    )


def test_webhook_rejects_invalid_signature(client):
    body = {
        "monto": "1500.00", "referenciaNumerica": "0000014", "claveRastreo": "STP-X",
        "fechaOperacion": "2026-09-15T10:00:00", "cuentaBeneficiario": "012180001547896321",
    }
    response = _signed_request(client, body, secret="firma-incorrecta")
    assert response.status_code == 401


def test_webhook_processes_valid_signed_deposit(client):
    client.post("/properties", json={"identificador": "Casa 14"})

    @asynccontextmanager
    async def fake_tenant_session(schema_name):
        async with client.db_session_factory() as session:
            yield session

    async def override_control_session():
        async with client.db_session_factory() as session:
            yield session

    app.dependency_overrides[control_session] = override_control_session

    body = {
        "monto": "1500.00", "referenciaNumerica": "0000014", "claveRastreo": "STP-WEBHOOK-1",
        "fechaOperacion": "2026-09-15T10:00:00", "cuentaBeneficiario": "012180001547896321",
    }
    with patch.object(dps, "tenant_session", fake_tenant_session):
        response = _signed_request(client, body)

    del app.dependency_overrides[control_session]

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["payment_estado"] == "confirmado"


def test_webhook_refuses_the_placeholder_secret_in_production(client):
    """
    F2-21: stp_webhook_secret trae un default público y conocido
    ("cambia-esto-en-produccion") para no tronar el arranque en dev — pero un
    secreto de firma sin configurar en PRODUCCIÓN es "fail open": cualquiera
    que haya leído el repo puede firmar un depósito falso. En producción debe
    rechazarse de plano en vez de aceptar webhooks firmados con ese secreto
    público.
    """
    body = {
        "monto": "1500.00", "referenciaNumerica": "0000014", "claveRastreo": "STP-X",
        "fechaOperacion": "2026-09-15T10:00:00", "cuentaBeneficiario": "012180001547896321",
    }
    assert settings.stp_webhook_secret == "cambia-esto-en-produccion"
    original_environment = settings.environment
    settings.environment = "production"
    try:
        response = _signed_request(client, body)
    finally:
        settings.environment = original_environment

    assert response.status_code == 503


def test_webhook_does_not_leak_internal_field_names_on_invalid_payload(client):
    """F2-21: un payload inválido regresaba el detalle crudo de la excepción (nombres de campos internos) al llamador."""
    response = _signed_request(client, {"monto": "1500.00"})  # faltan referenciaNumerica, claveRastreo, etc.
    assert response.status_code == 422
    assert response.json()["detail"] == "Payload de STP inválido"
