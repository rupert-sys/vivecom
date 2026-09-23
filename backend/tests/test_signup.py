"""
Landing de bienvenida (F3-06 ampliado): alta de un condominio sin intervención manual del equipo, en dos pasos
— datos del condominio (nombre, cantidad de viviendas) y datos de quien se registra (nombre, teléfono). No pide
CLABE ni que el admin invente su propio email/contraseña (ver api/signup.py).

No se puede probar POST /signup de punta a punta contra esta suite: usa provision_tenant_con_casas(), que
ejecuta CREATE SCHEMA y SET search_path — sintaxis específica de Postgres que SQLite ni siquiera entiende
(mismo límite que el resto de las pruebas de aprovisionamiento de tenants). Se prueba en cambio la capa de
validación (TenantSignupRequest), que sí es pura; el flujo real se verificó a mano contra el backend con
Postgres.app real. tenant_domain.py (slug/dominio) y /residents/activar sí se prueban de punta a punta —
ver test_tenant_domain.py y test_resident_activation.py — porque no dependen de CREATE SCHEMA.
"""

import pytest
from pydantic import ValidationError

from app.schemas.signup import MAX_CASAS_POR_SIGNUP, TenantSignupRequest


def _payload(**overrides):
    base = {
        "nombre_condominio": "Residencial Las Fuentes",
        "cantidad_casas": 20,
        "nombre_admin": "Ruperto Villalobos",
        "telefono_admin": "5555555555",
    }
    base.update(overrides)
    return base


def test_payload_valido_no_lanza_error():
    TenantSignupRequest(**_payload())


def test_nombre_de_condominio_vacio_es_rechazado():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(nombre_condominio=""))


def test_cantidad_de_casas_debe_ser_al_menos_una():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(cantidad_casas=0))


def test_cantidad_de_casas_tiene_un_tope():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(cantidad_casas=MAX_CASAS_POR_SIGNUP + 1))
    TenantSignupRequest(**_payload(cantidad_casas=MAX_CASAS_POR_SIGNUP))  # el tope mismo sí se acepta


def test_nombre_del_admin_vacio_es_rechazado():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(nombre_admin=""))


def test_telefono_del_admin_vacio_es_rechazado():
    with pytest.raises(ValidationError):
        TenantSignupRequest(**_payload(telefono_admin=""))
