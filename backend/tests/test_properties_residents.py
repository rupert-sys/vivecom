"""
Pruebas de los endpoints de Property/Resident. El fixture `client` vive en
tests/conftest.py (compartido con las demás pruebas).
"""

import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str, property_id: str | None = None):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id)

    app.dependency_overrides[get_current_user] = override


def test_create_and_list_property(client):
    response = client.post("/properties", json={"identificador": "Casa 14"})
    assert response.status_code == 201
    body = response.json()
    assert body["identificador"] == "Casa 14"

    response = client.get("/properties")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_resident_and_link_to_property(client):
    prop = client.post("/properties", json={"identificador": "Casa 20"}).json()
    resident = client.post(
        "/residents", json={"nombre": "Ana Pérez", "telefono": "5511112222"}
    ).json()

    link = client.post(
        f"/properties/{prop['id']}/residents",
        json={"resident_id": resident["id"], "rol": "propietario"},
    )
    assert link.status_code == 201

    residents_of_property = client.get(f"/properties/{prop['id']}/residents")
    assert residents_of_property.status_code == 200
    assert len(residents_of_property.json()) == 1
    assert residents_of_property.json()[0]["nombre"] == "Ana Pérez"


def test_create_property_does_not_error_after_commit(client):
    """
    Regresión: crear una vivienda no debe intentar releer la fila después del
    commit (db.refresh) porque el search_path del tenant es transaccional y
    ya no aplica — eso causaba un 500 "relation does not exist" en Postgres real
    (invisible en esta prueba con SQLite, pero la dejamos como documentación
    del bug y para detectar si el patrón de refresh() vuelve a aparecer).
    """
    response = client.post("/properties", json={"identificador": "Casa 99"})
    assert response.status_code == 201
    assert response.json()["identificador"] == "Casa 99"
    assert "id" in response.json()


def test_same_resident_can_link_to_multiple_independent_properties(client):
    """Ver alcance sección 2: un propietario puede tener varias viviendas."""
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()
    resident = client.post("/residents", json={"nombre": "Luis Gómez", "telefono": "5533334444"}).json()

    for prop in (prop_a, prop_b):
        link = client.post(
            f"/properties/{prop['id']}/residents",
            json={"resident_id": resident["id"], "rol": "propietario"},
        )
        assert link.status_code == 201

    assert len(client.get(f"/properties/{prop_a['id']}/residents").json()) == 1
    assert len(client.get(f"/properties/{prop_b['id']}/residents").json()) == 1


def test_a_resident_cannot_list_or_read_residents_of_the_whole_tenant(client):
    """
    F2-21: GET /residents y GET /residents/{id} no tenían NINGÚN control de
    rol — cualquier residente autenticado podía listar nombre/teléfono/email
    de TODOS los residentes del condominio (IDOR). Ahora son staff-only
    (admin/tesorero/guardia).
    """
    resident = client.post("/residents", json={"nombre": "Ana Pérez", "telefono": "5511112222"}).json()

    _como("residente")
    assert client.get("/residents").status_code == 403
    assert client.get(f"/residents/{resident['id']}").status_code == 403


def test_a_resident_cannot_list_residents_of_another_property(client):
    """F2-21: GET /properties/{id}/residents no verificaba que la vivienda fuera la propia."""
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()
    resident = client.post("/residents", json={"nombre": "Luis Gómez", "telefono": "5533334444"}).json()
    client.post(f"/properties/{prop_a['id']}/residents", json={"resident_id": resident["id"], "rol": "propietario"})

    _como("residente", property_id=prop_b["id"])
    assert client.get(f"/properties/{prop_a['id']}/residents").status_code == 403

    _como("residente", property_id=prop_a["id"])
    assert client.get(f"/properties/{prop_a['id']}/residents").status_code == 200

    _como("guardia")
    assert client.get(f"/properties/{prop_a['id']}/residents").status_code == 200


def test_a_resident_cannot_read_another_propertys_payment_reference(client):
    """
    F2-21: GET /properties/{id} regresa referencia_pago y saldo_a_favor sin
    verificar dueño — un residente podía leer los de OTRA vivienda con solo
    adivinar/conocer su UUID.
    """
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()

    _como("residente", property_id=prop_b["id"])
    assert client.get(f"/properties/{prop_a['id']}").status_code == 403

    _como("residente", property_id=prop_a["id"])
    assert client.get(f"/properties/{prop_a['id']}").status_code == 200

    _como("tesorero")
    assert client.get(f"/properties/{prop_a['id']}").status_code == 200
