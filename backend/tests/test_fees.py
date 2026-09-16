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
