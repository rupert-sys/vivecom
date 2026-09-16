def test_get_clabe_returns_seeded_value(client):
    response = client.get("/tenant/clabe")
    assert response.status_code == 200
    assert response.json()["clabe_destino"] == "012180001547896321"


def test_change_clabe_requires_explicit_confirmation(client):
    """Sin confirmo_cambio=true, el cambio debe rechazarse (alcance HU-A07)."""
    response = client.patch(
        "/tenant/clabe", json={"clabe_nueva": "123456789012345678", "confirmo_cambio": False}
    )
    assert response.status_code == 422

    # La CLABE no debe haber cambiado.
    assert client.get("/tenant/clabe").json()["clabe_destino"] == "012180001547896321"


def test_change_clabe_rejects_invalid_format(client):
    response = client.patch(
        "/tenant/clabe", json={"clabe_nueva": "no-es-una-clabe", "confirmo_cambio": True}
    )
    assert response.status_code == 422


def test_change_clabe_with_confirmation_succeeds_and_logs(client):
    response = client.patch(
        "/tenant/clabe", json={"clabe_nueva": "999888777666555444", "confirmo_cambio": True}
    )
    assert response.status_code == 200
    assert response.json()["clabe_destino"] == "999888777666555444"

    history = client.get("/tenant/clabe/historial")
    assert history.status_code == 200
    assert len(history.json()) == 1
    entry = history.json()[0]
    assert entry["clabe_anterior"] == "012180001547896321"
    assert entry["clabe_nueva"] == "999888777666555444"
