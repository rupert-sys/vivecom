"""
F3-06: alta de un condominio nuevo sin intervención manual del equipo.

No se puede probar el endpoint POST /signup de punta a punta contra esta
suite: usa control_session()/provision_tenant() directamente (igual que
POST /auth/login, ver test_users.py), que además ejecuta CREATE SCHEMA y
SET search_path — sintaxis específica de Postgres que SQLite ni siquiera
entiende. Se prueba en cambio la capa de validación (TenantSignupRequest),
que sí es pura y no toca la base de datos; el flujo real (éxito, email
duplicado) se verificó a mano contra el backend con Postgres.app real.
"""

import pytest
from pydantic import ValidationError

from app.schemas.signup import TenantSignupRequest


def _payload(**overrides):
    base = {
        "nombre_condominio": "Residencial Las Fuentes",
        "clabe_destino": "012180001547896321",
        "admin_email": "admin@condo.mx",
        "admin_password": "clave-temporal-123",
    }
    base.update(overrides)
    return base


def test_payload_valido_no_lanza_error():
    TenantSignupRequest(**_payload())


def test_clabe_debe_tener_18_digitos():
    with pytest.raises(ValidationError, match="18 dígitos"):
        TenantSignupRequest(**_payload(clabe_destino="123"))


def test_clabe_no_puede_tener_letras():
    with pytest.raises(ValidationError, match="18 dígitos"):
        TenantSignupRequest(**_payload(clabe_destino="01218000154789632X"))


def test_password_corta_es_rechazada():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(admin_password="corta"))


def test_email_invalido_es_rechazado():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(admin_email="no-es-un-email"))


def test_nombre_de_condominio_vacio_es_rechazado():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(nombre_condominio=""))
