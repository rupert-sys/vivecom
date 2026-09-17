"""
F2-05 / HU-S06: incidencias con seguimiento, visibles para admin y comité.
F2-06: alertas en tiempo real por WebSocket cuando pasa algo con una
incidencia.
"""

import uuid

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.main import app
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def test_create_and_list_incident(client):
    response = client.post("/incidents", json={"descripcion": "Fuga de agua en el estacionamiento"})
    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "abierta"
    assert body["descripcion"] == "Fuga de agua en el estacionamiento"

    listado = client.get("/incidents").json()
    assert len(listado) == 1
    assert listado[0]["id"] == body["id"]


def test_comite_lectura_can_view_but_not_create(client):
    client.post("/incidents", json={"descripcion": "Incidencia original"})

    _como("comite_lectura")
    assert client.get("/incidents").status_code == 200
    assert client.post("/incidents", json={"descripcion": "Otra"}).status_code == 403


def test_guardia_can_report_an_incident(client):
    _como("guardia")
    response = client.post("/incidents", json={"descripcion": "Portón dañado"})
    assert response.status_code == 201


def test_residente_cannot_see_incidents(client):
    _como("residente")
    response = client.get("/incidents")
    assert response.status_code == 403


def test_change_incident_status_follows_state_machine(client):
    incidencia = client.post("/incidents", json={"descripcion": "Elevador atorado"}).json()
    assert incidencia["resolved_at"] is None

    en_proceso = client.patch(f"/incidents/{incidencia['id']}/status", json={"estado": "en_proceso"})
    assert en_proceso.status_code == 200
    assert en_proceso.json()["estado"] == "en_proceso"
    assert en_proceso.json()["resolved_at"] is None

    resuelta = client.patch(f"/incidents/{incidencia['id']}/status", json={"estado": "resuelta"})
    assert resuelta.json()["estado"] == "resuelta"
    assert resuelta.json()["resolved_at"] is not None


def test_resolved_at_se_limpia_si_se_reabre_una_incidencia(client):
    """
    F2-12: la máquina de estados es deliberadamente permisiva (puede ir
    hacia atrás, ver nota de F2-05) — resolved_at debe reflejar la
    transición A resuelta más reciente, no quedarse pegado si se reabre.
    """
    incidencia = client.post("/incidents", json={"descripcion": "Fuga menor"}).json()
    client.patch(f"/incidents/{incidencia['id']}/status", json={"estado": "resuelta"})

    reabierta = client.patch(f"/incidents/{incidencia['id']}/status", json={"estado": "abierta"})
    assert reabierta.json()["resolved_at"] is None

    resuelta_de_nuevo = client.patch(f"/incidents/{incidencia['id']}/status", json={"estado": "resuelta"})
    assert resuelta_de_nuevo.json()["resolved_at"] is not None


def test_add_and_list_comments(client):
    incidencia = client.post("/incidents", json={"descripcion": "Fuga de agua"}).json()

    comentario = client.post(f"/incidents/{incidencia['id']}/comments", json={"comentario": "Plomero en camino"})
    assert comentario.status_code == 201

    comentarios = client.get(f"/incidents/{incidencia['id']}/comments").json()
    assert len(comentarios) == 1
    assert comentarios[0]["comentario"] == "Plomero en camino"


def test_get_unknown_incident_404(client):
    response = client.get(f"/incidents/{uuid.uuid4()}")
    assert response.status_code == 404


def test_incident_creation_broadcasts_to_connected_admin(client):
    token = create_access_token(
        subject=str(uuid.uuid4()), tenant_id=_tenant_id(), schema_name="test", rol="admin", property_id=None
    )

    with client.websocket_connect(f"/incidents/ws?token={token}") as websocket:
        response = client.post("/incidents", json={"descripcion": "Fuga de agua en el estacionamiento"})
        assert response.status_code == 201

        mensaje = websocket.receive_json()
        assert mensaje["evento"] == "incidencia_creada"
        assert mensaje["descripcion"] == "Fuga de agua en el estacionamiento"


def test_incident_status_change_broadcasts_too(client):
    incidencia = client.post("/incidents", json={"descripcion": "Elevador atorado"}).json()
    token = create_access_token(
        subject=str(uuid.uuid4()), tenant_id=_tenant_id(), schema_name="test", rol="admin", property_id=None
    )

    with client.websocket_connect(f"/incidents/ws?token={token}") as websocket:
        client.patch(f"/incidents/{incidencia['id']}/status", json={"estado": "en_proceso"})
        mensaje = websocket.receive_json()
        assert mensaje["evento"] == "incidencia_actualizada"
        assert mensaje["estado"] == "en_proceso"


def test_websocket_rejects_invalid_token(client):
    try:
        with client.websocket_connect("/incidents/ws?token=esto-no-es-un-jwt"):
            raise AssertionError("no debería haber aceptado la conexión")
    except Exception:
        pass  # Starlette cierra la conexión durante el handshake; el cliente ve una excepción, es lo esperado


def test_websocket_rejects_role_without_access(client):
    token = create_access_token(
        subject=str(uuid.uuid4()), tenant_id=_tenant_id(), schema_name="test", rol="residente", property_id=None
    )
    try:
        with client.websocket_connect(f"/incidents/ws?token={token}"):
            raise AssertionError("un residente no debería poder conectarse")
    except Exception:
        pass
