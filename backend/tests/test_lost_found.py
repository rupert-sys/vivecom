"""
F2-15 / HU-C05: objetos perdidos moderados — no aparecen públicamente hasta
que el administrador los autoriza.
"""

import uuid


def test_create_item_starts_pending_authorization(client):
    response = client.post("/lost-found", json={"descripcion": "Llavero azul encontrado en el lobby"})
    assert response.status_code == 201
    assert response.json()["estado"] == "pendiente_autorizacion"


def test_pending_item_hidden_from_list_and_get(client):
    from app.api.deps import get_current_user
    from app.main import app
    from app.schemas.auth import CurrentUser

    item = client.post("/lost-found", json={"descripcion": "Bicicleta gris"}).json()

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def como_residente():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="residente", property_id=None)

    app.dependency_overrides[get_current_user] = como_residente

    assert client.get("/lost-found").json() == []
    assert client.get(f"/lost-found/{item['id']}").status_code == 404


def test_admin_sees_pending_items(client):
    client.post("/lost-found", json={"descripcion": "Bicicleta gris"})
    assert len(client.get("/lost-found").json()) == 1


def test_moderate_item_authorizes_it(client):
    item = client.post("/lost-found", json={"descripcion": "Llavero azul"}).json()

    response = client.patch(f"/lost-found/{item['id']}/moderate", json={"estado": "autorizado"})
    assert response.status_code == 200
    assert response.json()["estado"] == "autorizado"

    from app.api.deps import get_current_user
    from app.main import app
    from app.schemas.auth import CurrentUser

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def como_residente():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol="residente", property_id=None)

    app.dependency_overrides[get_current_user] = como_residente
    listado = client.get("/lost-found").json()
    assert len(listado) == 1
    assert listado[0]["estado"] == "autorizado"


def test_get_unknown_item_404(client):
    response = client.get(f"/lost-found/{uuid.uuid4()}")
    assert response.status_code == 404
