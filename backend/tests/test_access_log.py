"""
F2-01 / HU-S01: registro de entradas y salidas. F2-03 / HU-S04: vehículos
asociados a un acceso.
"""

import uuid

import pytest

from app.api.access_log import register_entry, register_exit
from app.schemas.access_log import AccessLogCreate


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


def _instrumentar_orden_de_llamadas(db):
    """Envuelve db.execute/db.commit para registrar en qué orden se llaman.

    Sirve para verificar la garantía real detrás de la revisión de abajo
    (la lectura debe ocurrir ANTES del commit, no después) sin depender de
    Postgres: en SQLite ambos órdenes producen el mismo resultado, así que
    solo inspeccionando el ORDEN de las llamadas se puede detectar una
    regresión aquí.
    """
    llamadas = []
    execute_original = db.execute
    commit_original = db.commit

    async def execute_espia(*args, **kwargs):
        llamadas.append("execute")
        return await execute_original(*args, **kwargs)

    async def commit_espia(*args, **kwargs):
        llamadas.append("commit")
        return await commit_original(*args, **kwargs)

    db.execute = execute_espia
    db.commit = commit_espia
    return llamadas


@pytest.mark.asyncio
async def test_register_entry_reads_before_commit_not_after(client):
    """
    Revisión: register_entry() comiteaba y LUEGO llamaba a _to_read(), que
    vuelve a consultar Vehicle en la MISMA sesión — revienta contra Postgres
    real, porque el search_path del tenant se fija con is_local=true (ver
    core/database.py) y ya no aplica después de un commit ("relation vehicle
    does not exist"). Invisible en SQLite (esta suite no distingue schemas,
    ver conftest.py), así que no se puede reproducir el crash aquí — en vez
    de eso, esta prueba llama al endpoint directamente y verifica el ORDEN
    real de las llamadas a la sesión: el commit debe ser la ÚLTIMA operación,
    sin ningún execute() después.
    """
    client.get("/access-log")  # dispara la creación de tablas (ver conftest.py)

    async with client.db_session_factory() as db:
        llamadas = _instrumentar_orden_de_llamadas(db)
        payload = AccessLogCreate(tipo="proveedor", placas=["ABC-123"])

        resultado = await register_entry(payload, db)

    assert resultado.placas == ["ABC-123"]
    assert "commit" in llamadas
    assert llamadas[-1] == "commit"
    assert llamadas.count("execute") == 1


@pytest.mark.asyncio
async def test_register_exit_reads_before_commit_not_after(client):
    """Misma revisión que test_register_entry_reads_before_commit_not_after,
    para register_exit()."""
    client.get("/access-log")  # dispara la creación de tablas (ver conftest.py)

    async with client.db_session_factory() as db:
        log = await register_entry(AccessLogCreate(tipo="proveedor", placas=["DEF-456"]), db)

        llamadas = _instrumentar_orden_de_llamadas(db)
        resultado = await register_exit(log.id, db)

    assert resultado.hora_salida is not None
    assert resultado.placas == ["DEF-456"]
    assert "commit" in llamadas
    assert llamadas[-1] == "commit"
    assert llamadas.count("execute") == 1
