"""
F2-01 / HU-S01: registro de entradas y salidas. F2-03 / HU-S04: vehículos
asociados a un acceso.
"""

import uuid


def test_register_entry_and_exit(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    entrada = client.post("/access-log", json={"property_id": prop["id"], "tipo": "residente"})
    assert entrada.status_code == 201
    body = entrada.json()
    assert body["hora_salida"] is None

    salida = client.post(f"/access-log/{body['id']}/exit")
    assert salida.status_code == 200
    assert salida.json()["hora_salida"] is not None


def test_register_entry_with_vehicle_plates(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    response = client.post(
        "/access-log", json={"property_id": prop["id"], "tipo": "visitante", "placas": ["ABC-123", "XYZ-999"]}
    )
    assert response.status_code == 201
    assert sorted(response.json()["placas"]) == ["ABC-123", "XYZ-999"]


def test_register_entry_without_property_for_provider(client):
    """HU-S01: un proveedor puede no tener vivienda asociada."""
    response = client.post("/access-log", json={"tipo": "proveedor"})
    assert response.status_code == 201
    assert response.json()["property_id"] is None


def test_register_entry_with_unknown_property_404(client):
    response = client.post("/access-log", json={"property_id": str(uuid.uuid4()), "tipo": "residente"})
    assert response.status_code == 404


def test_register_exit_twice_fails(client):
    entrada = client.post("/access-log", json={"tipo": "proveedor"}).json()
    client.post(f"/access-log/{entrada['id']}/exit")

    response = client.post(f"/access-log/{entrada['id']}/exit")
    assert response.status_code == 409


def test_list_access_logs_filters_by_property_and_tipo(client):
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()
    client.post("/access-log", json={"property_id": prop_a["id"], "tipo": "residente"})
    client.post("/access-log", json={"property_id": prop_b["id"], "tipo": "visitante"})
    client.post("/access-log", json={"tipo": "proveedor"})

    solo_prop_a = client.get("/access-log", params={"property_id": prop_a["id"]}).json()
    assert len(solo_prop_a) == 1
    assert solo_prop_a[0]["tipo"] == "residente"

    solo_visitantes = client.get("/access-log", params={"tipo": "visitante"}).json()
    assert len(solo_visitantes) == 1
    assert solo_visitantes[0]["property_id"] == prop_b["id"]

    assert len(client.get("/access-log").json()) == 3


def test_get_unknown_access_log_404(client):
    response = client.get(f"/access-log/{uuid.uuid4()}")
    assert response.status_code == 404
