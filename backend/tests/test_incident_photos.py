"""
Foto de una incidencia levantada desde la caseta: se sube como archivo (kind=incidencia) y la
incidencia la referencia; se entrega como enlace firmado.
"""

import uuid
from urllib.parse import urlsplit

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser

JPEG = b"\xff\xd8\xff\xe0" + b"\x01" * 80


def _como(rol: str, user_id: str | None = None) -> str:
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id
    uid = user_id or str(uuid.uuid4())

    def override():
        return CurrentUser(user_id=uid, tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override
    return uid


def _foto(client, kind="incidencia") -> dict:
    respuesta = client.post("/files", files={"file": ("foto.jpg", JPEG, "application/octet-stream")}, data={"kind": kind})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _descargar(client, url: str):
    partes = urlsplit(url)
    return client.get(f"{partes.path}?{partes.query}")


def test_la_incidencia_con_foto_subida_se_lee_con_un_enlace_que_abre_la_foto(client):
    _como("guardia")
    foto = _foto(client)
    creada = client.post("/incidents", json={"descripcion": "Luminaria fundida", "foto_archivo_id": foto["id"]})

    assert creada.status_code == 201
    assert f"/files/{foto['id']}/content?t=" in creada.json()["foto_url"]
    assert _descargar(client, creada.json()["foto_url"]).content == JPEG

    _como("comite_lectura")  # quien revisa las incidencias la ve en la lista y en el detalle
    listada = client.get("/incidents").json()[0]
    assert _descargar(client, listada["foto_url"]).status_code == 200
    detalle = client.get(f"/incidents/{listada['id']}").json()
    assert _descargar(client, detalle["foto_url"]).content == JPEG


def test_cambiar_el_estado_de_una_incidencia_conserva_su_foto_como_enlace(client):
    _como("guardia")
    creada = client.post("/incidents", json={"descripcion": "x", "foto_archivo_id": _foto(client)["id"]}).json()

    cambiada = client.patch(f"/incidents/{creada['id']}/status", json={"estado": "en_proceso"}).json()

    assert "/content?t=" in cambiada["foto_url"]


def test_una_incidencia_sigue_aceptando_un_enlace_de_texto_como_foto(client):
    _como("guardia")
    creada = client.post("/incidents", json={"descripcion": "x", "foto_url": "https://ejemplo.com/foto.jpg"})
    assert creada.json()["foto_url"] == "https://ejemplo.com/foto.jpg"


def test_solo_se_adjunta_una_foto_propia_y_de_incidencia(client):
    _como("guardia")
    ajena = _foto(client)
    _como("guardia")  # otro guardia
    assert client.post("/incidents", json={"descripcion": "x", "foto_archivo_id": ajena["id"]}).status_code == 422

    _como("tesorero")  # F0-12: gastos son de tesorería, no del administrador
    de_gasto = _foto(client, kind="gasto")
    _como("guardia")  # quien crea la incidencia sigue siendo guardia/admin/comité, no tesorería
    assert client.post("/incidents", json={"descripcion": "x", "foto_archivo_id": de_gasto["id"]}).status_code == 422
    assert client.post("/incidents", json={"descripcion": "x", "foto_archivo_id": str(uuid.uuid4())}).status_code == 422


def test_reintentar_la_sincronizacion_con_la_misma_foto_no_duplica_la_incidencia(client):
    _como("guardia")
    foto = _foto(client)
    cuerpo = {"descripcion": "Portón atorado", "client_id": str(uuid.uuid4()), "foto_archivo_id": foto["id"]}

    primera = client.post("/incidents", json=cuerpo)
    repetida = client.post("/incidents", json=cuerpo)

    assert primera.status_code == 201 and repetida.status_code == 201
    assert repetida.json()["id"] == primera.json()["id"]
    assert len(client.get("/incidents").json()) == 1


def test_el_mismo_client_id_con_otra_foto_es_un_conflicto(client):
    _como("guardia")
    cid = str(uuid.uuid4())
    client.post("/incidents", json={"descripcion": "x", "client_id": cid, "foto_archivo_id": _foto(client)["id"]})
    otra = client.post("/incidents", json={"descripcion": "x", "client_id": cid, "foto_archivo_id": _foto(client)["id"]})
    assert otra.status_code == 409


def test_quien_puede_pedir_el_enlace_de_la_foto_de_una_incidencia(client):
    guardia = _como("guardia")
    foto = _foto(client)
    for rol in ("admin", "comite_lectura", "comite_aprobador"):
        _como(rol)
        assert client.get(f"/files/{foto['id']}/link").status_code == 200, rol
    _como("residente")
    assert client.get(f"/files/{foto['id']}/link").status_code == 404
    _como("guardia", user_id=guardia)
    assert client.get(f"/files/{foto['id']}/link").status_code == 200
