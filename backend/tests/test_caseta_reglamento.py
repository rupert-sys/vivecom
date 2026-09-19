"""
Lo que la app caseta necesita del backend: paquetes capturados sin conexión
(idempotentes por client_id) y códigos de un solo uso que el guardia emite a
proveedores (reglamento Art. 17 V.3: el acceso de proveedores requiere
autorización).
"""

import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _como(rol: str, property_id: str | None = None):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id
        )

    app.dependency_overrides[get_current_user] = override


def _vivienda(client, nombre="Casa 1") -> str:
    return client.post("/properties", json={"identificador": nombre}).json()["id"]


# ---------- Paquetes sin conexión ----------


def test_un_reintento_de_sync_con_el_mismo_client_id_no_duplica_el_paquete(client):
    prop = _vivienda(client)
    _como("guardia")
    cid = str(uuid.uuid4())
    primero = client.post("/packages", json={"property_id": prop, "client_id": cid})
    repetido = client.post("/packages", json={"property_id": prop, "client_id": cid})

    assert primero.status_code == 201 and repetido.status_code == 201
    assert repetido.json()["id"] == primero.json()["id"]
    assert len(client.get("/packages").json()) == 1


def test_el_mismo_client_id_para_otra_vivienda_es_un_conflicto(client):
    una, otra = _vivienda(client, "Casa 1"), _vivienda(client, "Casa 2")
    _como("guardia")
    cid = str(uuid.uuid4())
    client.post("/packages", json={"property_id": una, "client_id": cid})
    assert client.post("/packages", json={"property_id": otra, "client_id": cid}).status_code == 409


def test_sin_client_id_cada_registro_es_un_paquete_nuevo(client):
    prop = _vivienda(client)
    _como("guardia")
    client.post("/packages", json={"property_id": prop})
    client.post("/packages", json={"property_id": prop})
    assert len(client.get("/packages").json()) == 2


# ---------- Códigos de proveedor ----------


def test_el_guardia_emite_un_codigo_de_proveedor_y_al_validarlo_ve_quien_es_y_a_donde_va(client):
    prop = _vivienda(client, "Casa 4")
    _como("guardia")
    emitido = client.post("/visitor-qr/provider", json={"descripcion": "Plomería López", "property_id": prop})
    assert emitido.status_code == 201
    codigo = emitido.json()
    assert (codigo["tipo"], codigo["descripcion"], codigo["property_id"]) == ("proveedor", "Plomería López", prop)

    validado = client.post(f"/visitor-qr/{codigo['codigo']}/validate").json()
    assert validado == {
        "valido": True, "motivo": None, "property_id": prop, "tipo": "proveedor",
        "descripcion": "Plomería López", "vivienda": "Casa 4",
    }
    assert client.post(f"/visitor-qr/{codigo['codigo']}/validate").json()["motivo"] == "ya_usado"


def test_un_proveedor_del_condominio_en_general_no_lleva_vivienda(client):
    _como("guardia")
    codigo = client.post("/visitor-qr/provider", json={"descripcion": "Jardinería"}).json()
    assert codigo["property_id"] is None

    validado = client.post(f"/visitor-qr/{codigo['codigo']}/validate").json()
    assert validado["valido"] is True and validado["vivienda"] is None and validado["tipo"] == "proveedor"


def test_el_codigo_de_una_visita_al_validarse_dice_a_que_vivienda_va(client):
    prop = _vivienda(client, "Casa 7")
    _como("residente", property_id=prop)
    codigo = client.post("/visitor-qr").json()
    assert codigo["tipo"] == "visitante"

    _como("guardia")
    validado = client.post(f"/visitor-qr/{codigo['codigo']}/validate").json()
    assert (validado["tipo"], validado["vivienda"]) == ("visitante", "Casa 7")


def test_un_residente_no_puede_emitir_codigos_de_proveedor(client):
    _como("residente", property_id=_vivienda(client))
    assert client.post("/visitor-qr/provider", json={"descripcion": "X"}).status_code == 403


def test_el_codigo_de_proveedor_valida_la_vivienda_y_la_descripcion(client):
    _como("guardia")
    assert client.post("/visitor-qr/provider", json={"descripcion": "X", "property_id": str(uuid.uuid4())}).status_code == 404
    assert client.post("/visitor-qr/provider", json={"descripcion": ""}).status_code == 422


def test_un_codigo_inexistente_sigue_rechazandose_sin_datos_de_vivienda(client):
    _como("guardia")
    assert client.post("/visitor-qr/no-existe/validate").json() == {
        "valido": False, "motivo": "no_existe", "property_id": None, "tipo": None, "descripcion": None, "vivienda": None,
    }
