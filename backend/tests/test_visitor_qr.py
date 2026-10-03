"""
F2-02 / HU-S02: QR de acceso temporal generado por el residente.
F2-03 / HU-S03: validación del QR por el guardia, de un solo uso.
"""

import json
import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _como_residente(property_id: str):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="residente",
            property_id=property_id,
        )

    app.dependency_overrides[get_current_user] = override


def _como_guardia():
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="guardia", property_id=None
        )

    app.dependency_overrides[get_current_user] = override


def test_resident_generates_qr(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    _como_residente(prop["id"])
    response = client.post("/visitor-qr", json={"nombre_visitante": "Juan Pérez", "numero_personas": 2})
    assert response.status_code == 201
    body = response.json()
    assert body["property_id"] == prop["id"]
    assert body["usado"] is False
    assert len(body["codigo"]) > 10
    assert body["nombre_visitante"] == "Juan Pérez"
    assert body["numero_personas"] == 2


def test_qr_payload_trae_lo_necesario_para_leerse_sin_conexion(client):
    prop = client.post("/properties", json={"identificador": "Casa 7"}).json()
    _como_residente(prop["id"])
    body = client.post("/visitor-qr", json={"nombre_visitante": "Ana Torres", "numero_personas": 3}).json()

    payload = json.loads(body["qr_payload"])
    assert payload["codigo"] == body["codigo"]
    assert payload["nombre_visitante"] == "Ana Torres"
    assert payload["numero_personas"] == 3
    assert payload["vivienda"] == "Casa 7"


def test_resident_without_property_cannot_generate_qr(client):
    response = client.post("/visitor-qr", json={"nombre_visitante": "Juan Pérez"})  # admin del fixture, sin property_id
    assert response.status_code == 400


def test_resident_debe_dar_el_nombre_del_visitante(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como_residente(prop["id"])
    response = client.post("/visitor-qr", json={"nombre_visitante": ""})
    assert response.status_code == 422


def test_guard_validates_qr_successfully(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como_residente(prop["id"])
    qr = client.post("/visitor-qr", json={"nombre_visitante": "Juan Pérez"}).json()

    _como_guardia()
    response = client.post(f"/visitor-qr/{qr['codigo']}/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["valido"] is True
    assert body["property_id"] == prop["id"]
    assert body["nombre_visitante"] == "Juan Pérez"


def test_validar_un_qr_abre_su_acceso_en_la_bitacora(client):
    """Bug real encontrado probando en dispositivo: confirmar el QR marcaba el código como usado y
    mostraba "Acceso autorizado" en pantalla, pero nunca creaba nada en la bitácora — el visitante no
    aparecía después en "accesos abiertos". Ver la nota en visitor_qr_service.validate_and_consume_qr."""
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como_residente(prop["id"])
    qr = client.post("/visitor-qr", json={"nombre_visitante": "Juan Pérez", "numero_personas": 3}).json()

    _como_guardia()
    client.post(f"/visitor-qr/{qr['codigo']}/validate")

    abiertos = client.get("/access-log").json()
    assert len(abiertos) == 1
    acceso = abiertos[0]
    assert acceso["property_id"] == prop["id"]
    assert acceso["tipo"] == "visitante"
    assert acceso["nombre_visitante"] == "Juan Pérez"
    assert acceso["acompanantes"] == 3
    assert acceso["hora_salida"] is None


def test_qr_cannot_be_used_twice(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como_residente(prop["id"])
    qr = client.post("/visitor-qr", json={"nombre_visitante": "Juan Pérez"}).json()

    _como_guardia()
    client.post(f"/visitor-qr/{qr['codigo']}/validate")
    segunda_vez = client.post(f"/visitor-qr/{qr['codigo']}/validate")

    assert segunda_vez.status_code == 200  # el endpoint responde 200 con valido=False, no un error HTTP
    body = segunda_vez.json()
    assert body["valido"] is False
    assert body["motivo"] == "ya_usado"


def test_validate_unknown_code(client):
    response = client.post("/visitor-qr/codigo-inventado/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["valido"] is False
    assert body["motivo"] == "no_existe"
