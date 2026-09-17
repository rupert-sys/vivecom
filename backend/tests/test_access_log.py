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


def test_list_access_logs_keeps_each_ones_own_plates_separate(client):
    """
    F2-22: list_access_logs() antes hacía una consulta a Vehicle POR CADA
    log (N+1) llamando _to_read() en un loop; se corrigió con una sola
    consulta con IN (...) que agrupa las placas por access_log_id en
    memoria. La forma más real de romper ese agrupamiento es mezclar las
    placas de un log con las de otro — esta prueba usa 3 logs con placas
    distintas (una sin ninguna) para exigir que cada uno traiga solo las
    suyas.
    """
    client.post("/access-log", json={"tipo": "visitante", "placas": ["AAA-111"]})
    client.post("/access-log", json={"tipo": "visitante", "placas": ["BBB-222", "CCC-333"]})
    client.post("/access-log", json={"tipo": "proveedor", "placas": []})

    listado = client.get("/access-log").json()
    assert len(listado) == 3
    placas_por_log = {tuple(sorted(entrada["placas"])) for entrada in listado}
    assert placas_por_log == {("AAA-111",), ("BBB-222", "CCC-333"), ()}


def test_get_unknown_access_log_404(client):
    response = client.get(f"/access-log/{uuid.uuid4()}")
    assert response.status_code == 404


def test_register_exit_still_returns_the_plates_registered_at_entry(client):
    """
    Revisión: tanto register_entry() como register_exit() armaban su
    respuesta re-consultando Vehicle DESPUÉS de comitear — revienta contra
    Postgres real (el search_path del tenant, is_local=true, ya no aplica en
    esa segunda consulta), mismo bug ya corregido en polls.py. Invisible en
    SQLite (esta suite). register_entry() se corrigió sin volver a consultar
    (ya conoce las placas del propio payload); register_exit() se corrigió
    consultando Vehicle ANTES del commit final, en vez de después. Esta
    prueba fija que register_exit() siga regresando las placas correctas
    después del fix.
    """
    entrada = client.post("/access-log", json={"tipo": "visitante", "placas": ["ABC-123"]}).json()

    salida = client.post(f"/access-log/{entrada['id']}/exit")
    assert salida.status_code == 200
    assert salida.json()["placas"] == ["ABC-123"]
    assert salida.json()["hora_salida"] is not None


def test_register_entry_with_client_id_is_idempotent_on_retry(client):
    """
    F2-07/F2-11: la app caseta reintenta la sincronización de un registro
    encolado offline si el primer intento no confirmó respuesta (aunque sí
    haya llegado al servidor) — un reintento con el MISMO client_id y el
    mismo payload no debe crear un segundo registro.
    """
    client_id = str(uuid.uuid4())
    payload = {"tipo": "visitante", "placas": ["ABC-123"], "client_id": client_id}

    primero = client.post("/access-log", json=payload)
    assert primero.status_code == 201

    segundo = client.post("/access-log", json=payload)
    assert segundo.status_code == 201
    assert segundo.json()["id"] == primero.json()["id"]

    listado = client.get("/access-log").json()
    assert len([log for log in listado if log["id"] == primero.json()["id"]]) == 1


def test_register_entry_with_reused_client_id_and_different_payload_is_a_conflict(client):
    """Dos registros distintos compitiendo por el mismo client_id es un bug del cliente, no un reintento legítimo."""
    client_id = str(uuid.uuid4())
    client.post("/access-log", json={"tipo": "visitante", "client_id": client_id})

    conflicto = client.post("/access-log", json={"tipo": "residente", "client_id": client_id})
    assert conflicto.status_code == 409
