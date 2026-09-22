"""Viviendas: quién vive ahí y si es propietario o inquilino, para la lista del panel (residents_summary_service.py)."""



def _vivienda(client, identificador="Casa 1"):
    return client.post("/properties", json={"identificador": identificador}).json()["id"]


def _residente(client, nombre, telefono="5555550100"):
    return client.post("/residents", json={"nombre": nombre, "telefono": telefono}).json()["id"]


def _ligar(client, property_id, resident_id, rol):
    client.post(f"/properties/{property_id}/residents", json={"resident_id": resident_id, "rol": rol})


def test_una_vivienda_sin_residentes_no_tiene_principal(client):
    _vivienda(client)
    fila = client.get("/properties").json()[0]
    assert (fila["residente_principal"], fila["residente_principal_rol"], fila["total_residentes"]) == (None, None, 0)


def test_el_propietario_es_el_principal_aunque_se_ligue_despues_que_el_inquilino(client):
    v = _vivienda(client)
    inquilino = _residente(client, "Luis Peña")
    propietario = _residente(client, "Mariana Ortega")
    _ligar(client, v, inquilino, "inquilino")
    _ligar(client, v, propietario, "propietario")

    fila = client.get("/properties").json()[0]
    assert (fila["residente_principal"], fila["residente_principal_rol"], fila["total_residentes"]) == ("Mariana Ortega", "propietario", 2)


def test_sin_propietario_el_principal_es_el_inquilino(client):
    v = _vivienda(client)
    _ligar(client, v, _residente(client, "Luis Peña"), "inquilino")

    fila = client.get("/properties").json()[0]
    assert (fila["residente_principal"], fila["residente_principal_rol"]) == ("Luis Peña", "inquilino")


def test_dos_propietarios_el_principal_es_alfabetico(client):
    v = _vivienda(client)
    _ligar(client, v, _residente(client, "Zoe Ramírez"), "propietario")
    _ligar(client, v, _residente(client, "Ana Beltrán"), "propietario")

    fila = client.get("/properties").json()[0]
    assert (fila["residente_principal"], fila["total_residentes"]) == ("Ana Beltrán", 2)


def test_get_una_vivienda_tambien_trae_el_residente_principal(client):
    v = _vivienda(client)
    _ligar(client, v, _residente(client, "Mariana Ortega"), "propietario")

    fila = client.get(f"/properties/{v}").json()
    assert fila["residente_principal"] == "Mariana Ortega"


def test_varias_viviendas_no_se_cruzan_entre_si(client):
    v1 = _vivienda(client, "Casa 1")
    v2 = _vivienda(client, "Casa 2")
    _ligar(client, v1, _residente(client, "Mariana Ortega"), "propietario")
    _ligar(client, v2, _residente(client, "Luis Peña"), "inquilino")

    por_id = {f["id"]: f for f in client.get("/properties").json()}
    assert por_id[v1]["residente_principal"] == "Mariana Ortega"
    assert por_id[v2]["residente_principal"] == "Luis Peña"
