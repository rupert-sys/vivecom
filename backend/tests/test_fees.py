def test_create_and_list_fee(client):
    response = client.post(
        "/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-10-01"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["monto"] == 1500.00
    assert body["periodicidad"] == "mensual"

    response = client.get("/fees")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_fee_monto(client):
    fee = client.post(
        "/fees", json={"monto": 1000.00, "periodicidad": "mensual", "activa_desde": "2026-10-01"}
    ).json()

    response = client.patch(f"/fees/{fee['id']}", json={"monto": 1200.00})
    assert response.status_code == 200
    assert response.json()["monto"] == 1200.00
    # La periodicidad no se tocó, debe seguir igual.
    assert response.json()["periodicidad"] == "mensual"


def test_global_rules_are_not_per_tenant_configurable(client):
    """
    El recargo por mora es una regla global de la plataforma (alcance sección
    3.1, sección 9 resuelta) — este endpoint solo la expone, no permite
    cambiarla por tenant.
    """
    response = client.get("/fees/global-rules")
    assert response.status_code == 200
    body = response.json()
    assert body["recargo_porcentaje"] == 0.10
    assert body["recargo_dia_del_mes"] == 6


def test_delete_fee_sin_cargos(client):
    fee = client.post(
        "/fees", json={"monto": 1000.00, "periodicidad": "mensual", "activa_desde": "2026-10-01"}
    ).json()

    response = client.delete(f"/fees/{fee['id']}")

    assert response.status_code == 204
    assert client.get("/fees").json() == []


def test_delete_fee_inexistente_es_404(client):
    import uuid

    assert client.delete(f"/fees/{uuid.uuid4()}").status_code == 404


def test_no_se_puede_eliminar_una_cuota_que_ya_genero_cargos(client):
    client.post("/properties", json={"identificador": "Casa 1"})
    fee = client.post(
        "/fees", json={"monto": 1000.00, "periodicidad": "mensual", "activa_desde": "2026-09-01"}
    ).json()
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})

    response = client.delete(f"/fees/{fee['id']}")

    assert response.status_code == 409
    assert len(client.get("/fees").json()) == 1  # sigue ahí


def test_solo_el_admin_elimina_cuotas(client):
    fee = client.post(
        "/fees", json={"monto": 1000.00, "periodicidad": "mensual", "activa_desde": "2026-10-01"}
    ).json()
    for rol in ("tesorero", "comite_aprobador", "residente", "guardia"):
        _como(rol)
        assert client.delete(f"/fees/{fee['id']}").status_code == 403


def _como(rol: str) -> None:
    import uuid

    from app.api.deps import get_current_user
    from app.main import app
    from app.schemas.auth import CurrentUser

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def test_una_cuota_unica_genera_un_solo_cargo_para_su_periodo_y_no_reemplaza_a_la_mensual(client):
    casa1 = client.post("/properties", json={"identificador": "Casa 1"}).json()
    client.post("/properties", json={"identificador": "Casa 2"})
    client.post("/fees", json={"monto": 1500.00, "periodicidad": "mensual", "activa_desde": "2026-01-01"})
    client.post("/fees", json={"monto": 5000.00, "periodicidad": "unica", "activa_desde": "2026-09-01"})

    septiembre = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"}).json()
    assert septiembre["cargos_generados"] == 4  # 2 viviendas × (mensual + única)

    estado = client.get(f"/properties/{casa1['id']}/statement").json()
    montos = sorted(c["monto_base"] for c in estado["cargos"])
    assert montos == [1500.0, 5000.0]  # a Casa 1 le tocaron las dos, cada una con su monto

    octubre = client.post("/fees/generate-charges", params={"periodo": "2026-10-01"}).json()
    assert octubre["cargos_generados"] == 2  # solo la mensual: la única ya no vuelve a aplicar


def test_reintentar_la_generacion_de_una_cuota_unica_no_duplica(client):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": 5000.00, "periodicidad": "unica", "activa_desde": "2026-09-01"})

    primera = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"}).json()
    segunda = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"}).json()

    assert (primera["cargos_generados"], segunda["cargos_generados"]) == (1, 0)


def test_una_cuota_semanal_se_puede_crear_y_hoy_genera_con_la_misma_cadencia_que_mensual(client):
    """
    Se puede elegir "semanal" (se guarda y se lista tal cual), pero facturar de verdad cada semana no está
    implementado: periodo/FeeCharge son mensuales en todo el sistema (recargo incluido). Documentado también en
    el modelo (Periodicidad.semanal).
    """
    client.post("/properties", json={"identificador": "Casa 1"})
    creada = client.post("/fees", json={"monto": 200.00, "periodicidad": "semanal", "activa_desde": "2026-09-01"})
    assert creada.status_code == 201 and creada.json()["periodicidad"] == "semanal"

    generados = client.post("/fees/generate-charges", params={"periodo": "2026-09-01"}).json()
    assert generados["cargos_generados"] == 1
