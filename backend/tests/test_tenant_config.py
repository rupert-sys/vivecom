import uuid

import pytest
from sqlalchemy import select

from app.models.clabe_change_log import ClabeChangeLog
from app.models.tenant import Tenant


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


@pytest.mark.asyncio
async def test_change_clabe_rejects_a_clabe_already_used_by_another_tenant(client):
    """
    Bug real (F1-29): la CLABE es el único mecanismo para enrutar un
    depósito SPEI al tenant correcto (ver deposit_processing_service.py) —
    sin este chequeo, dos tenants con la misma CLABE rompen ese
    enrutamiento para AMBOS con un 500, en vez de conciliar el depósito.
    """
    # Dispara la creación (perezosa) de las tablas antes de insertar a mano.
    client.get("/tenant/clabe")

    async with client.db_session_factory() as db:
        db.add(
            Tenant(
                id=uuid.uuid4(),
                nombre="Otro condominio",
                clabe_destino="111222333444555666",
                precio_por_vivienda=25.00,
                schema_name="tenant_otro",
            )
        )
        await db.commit()

    response = client.patch(
        "/tenant/clabe", json={"clabe_nueva": "111222333444555666", "confirmo_cambio": True}
    )

    assert response.status_code == 409
    assert client.get("/tenant/clabe").json()["clabe_destino"] == "012180001547896321"


@pytest.mark.asyncio
async def test_change_clabe_stores_a_naive_utc_timestamp(client):
    """
    Revisión (encontrada al construir el panel admin de F1-20 contra un
    Postgres real, no solo contra esta suite): change_clabe() guardaba
    datetime.now(timezone.utc) SIN .replace(tzinfo=None) — ClabeChangeLog.fecha
    es un DateTime naive (igual que el resto del proyecto). Contra SQLite
    (esta prueba) el valor aware se guarda sin quejarse, pero contra Postgres
    real revienta al insertar: "can't subtract offset-naive and
    offset-aware datetimes". No podemos reproducir el crash de Postgres
    aquí (limitación conocida de la suite, igual que con with_for_update()),
    pero sí podemos exigir que el propio código nunca vuelva a construir el
    registro con un datetime aware.
    """
    response = client.patch("/tenant/clabe", json={"clabe_nueva": "999888777666555444", "confirmo_cambio": True})
    assert response.status_code == 200

    async with client.db_session_factory() as db:
        log = (await db.execute(select(ClabeChangeLog))).scalar_one()
    assert log.fecha.tzinfo is None
