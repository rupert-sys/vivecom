"""
F2-16 / HU-C06: reservación de amenidades con bloqueo anti doble-booking.
F2-17 / HU-C07: flujo de aprobación con notificación y rechazo automático
por tiempo.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.api.deps import get_current_user
from app.main import app
from app.models.user import UserAccount
from app.schemas.auth import CurrentUser
from app.services.notification_providers.base import NotificationProvider
from app.services.reservation_service import (
    ReservaInvalida, create_reservation, process_reservation_timeouts, resolve_reservation,
)


class FakeNotificationProvider(NotificationProvider):
    def __init__(self):
        self.enviados: list[tuple[str, str]] = []

    async def send(self, telefono: str, mensaje: str) -> bool:
        self.enviados.append((telefono, mensaje))
        return True


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str, property_id: str | None = None, user_id: str | None = None):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(
            user_id=user_id or str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol,
            property_id=property_id,
        )

    app.dependency_overrides[get_current_user] = override


async def _crear_user_account(client, rol: str, resident_id=None) -> str:
    user_id = uuid.uuid4()
    async with client.db_session_factory() as db:
        db.add(
            UserAccount(id=user_id, resident_id=resident_id, email=f"{user_id}@test.com", password_hash="x", rol=rol)
        )
        await db.commit()
    return str(user_id)


def _en(dias: float) -> datetime:
    return (datetime.now(timezone.utc) + timedelta(days=dias)).replace(tzinfo=None, microsecond=0)


def _crear_amenidad(client, periodo_limite_horas=24):
    _como("admin")
    return client.post("/amenities", json={"nombre": "Salón de eventos", "periodo_limite_horas": periodo_limite_horas}).json()


def test_admin_creates_and_lists_amenity(client):
    amenidad = _crear_amenidad(client)
    assert amenidad["nombre"] == "Salón de eventos"
    assert len(client.get("/amenities").json()) == 1


def test_global_rules_endpoint(client):
    response = client.get("/reservations/global-rules")
    assert response.status_code == 200
    assert response.json()["anticipacion_minima_dias_sugerida"] == 2


@pytest.mark.asyncio
async def test_add_approver_requires_comite_aprobador_role(client):
    amenidad = _crear_amenidad(client)
    aprobador_id = await _crear_user_account(client, rol="residente")

    _como("admin")
    response = client.post(f"/amenities/{amenidad['id']}/approvers", json={"user_id": aprobador_id})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_reservation_success(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    aprobador_id = await _crear_user_account(client, rol="comite_aprobador")
    _como("admin")
    client.post(f"/amenities/{amenidad['id']}/approvers", json={"user_id": aprobador_id})

    _como("residente", property_id=prop["id"])
    response = client.post(
        "/reservations",
        json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(5.5).isoformat()},
    )
    assert response.status_code == 201
    assert response.json()["estado"] == "pendiente"


def test_reservation_requires_a_property(client):
    amenidad = _crear_amenidad(client)
    _como("residente")
    response = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(5.5).isoformat()}
    )
    assert response.status_code == 400


def test_reservation_in_the_past_rejected(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    _como("residente", property_id=prop["id"])
    response = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(-1).isoformat(), "fecha_fin": _en(-0.5).isoformat()}
    )
    assert response.status_code == 409


def test_double_booking_rejected(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    _como("residente", property_id=prop["id"])

    client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    )
    traslapada = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5.5).isoformat(), "fecha_fin": _en(6.5).isoformat()}
    )
    assert traslapada.status_code == 409


def test_non_overlapping_reservation_allowed(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    _como("residente", property_id=prop["id"])

    client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    )
    seguida = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(6).isoformat(), "fecha_fin": _en(7).isoformat()}
    )
    assert seguida.status_code == 201


def test_availability_endpoint_shows_busy_slots(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    _como("residente", property_id=prop["id"])
    client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    )

    ocupados = client.get(f"/amenities/{amenidad['id']}/availability").json()
    assert len(ocupados) == 1
    assert "property_id" not in ocupados[0]


@pytest.mark.asyncio
async def test_designated_approver_can_approve(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    aprobador_id = await _crear_user_account(client, rol="comite_aprobador")
    _como("admin")
    client.post(f"/amenities/{amenidad['id']}/approvers", json={"user_id": aprobador_id})

    _como("residente", property_id=prop["id"])
    reserva = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    ).json()

    _como("comite_aprobador", user_id=aprobador_id)
    response = client.post(f"/reservations/{reserva['id']}/approve")
    assert response.status_code == 200
    assert response.json()["estado"] == "aprobada"


@pytest.mark.asyncio
async def test_non_designated_approver_cannot_approve(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    otro_aprobador_id = await _crear_user_account(client, rol="comite_aprobador")  # no ligado a esta amenidad

    _como("residente", property_id=prop["id"])
    reserva = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    ).json()

    _como("comite_aprobador", user_id=otro_aprobador_id)
    response = client.post(f"/reservations/{reserva['id']}/approve")
    assert response.status_code == 403


def test_admin_can_approve_any_reservation(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)

    _como("residente", property_id=prop["id"])
    reserva = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    ).json()

    _como("admin")
    response = client.post(f"/reservations/{reserva['id']}/reject")
    assert response.status_code == 200
    assert response.json()["estado"] == "rechazada"


def test_resident_sees_only_own_reservations(client):
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()
    amenidad = _crear_amenidad(client)

    _como("residente", property_id=prop_a["id"])
    client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()}
    )
    _como("residente", property_id=prop_b["id"])
    client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(7).isoformat(), "fecha_fin": _en(8).isoformat()}
    )

    _como("residente", property_id=prop_a["id"])
    propias = client.get("/reservations").json()
    assert len(propias) == 1
    assert propias[0]["property_id"] == prop_a["id"]

    _como("admin")
    assert len(client.get("/reservations").json()) == 2


@pytest.mark.asyncio
async def test_reservation_request_notifies_approvers(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)
    resident = client.post("/residents", json={"nombre": "Luis Gómez", "telefono": "5533334444"}).json()
    aprobador_id = await _crear_user_account(client, rol="comite_aprobador", resident_id=uuid.UUID(resident["id"]))
    _como("admin")
    client.post(f"/amenities/{amenidad['id']}/approvers", json={"user_id": aprobador_id})

    from unittest.mock import AsyncMock, patch

    import app.api.reservations as reservations_module

    _como("residente", property_id=prop["id"])
    with patch.object(reservations_module._notification_provider, "send", AsyncMock(return_value=True)) as mock_send:
        client.post(
            "/reservations",
            json={"amenity_id": amenidad["id"], "fecha_inicio": _en(5).isoformat(), "fecha_fin": _en(6).isoformat()},
        )
    mock_send.assert_awaited_once()
    assert mock_send.call_args.args[0] == "5533334444"


@pytest.mark.asyncio
async def test_process_timeouts_auto_rejects_after_sla(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client, periodo_limite_horas=2)

    _como("residente", property_id=prop["id"])
    reserva = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(10).isoformat(), "fecha_fin": _en(11).isoformat()}
    ).json()

    ahora_mas_3h = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    async with client.db_session_factory() as db:
        resultado = await process_reservation_timeouts(db, ahora_mas_3h)

    assert resultado == {"rechazadas": 1, "expiradas": 0}
    _como("admin")
    assert client.get(f"/reservations/{reserva['id']}").json()["estado"] == "rechazada"


@pytest.mark.asyncio
async def test_process_timeouts_marks_expired_when_window_already_passed(client):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client, periodo_limite_horas=100)  # más largo que la ventana misma

    _como("residente", property_id=prop["id"])
    reserva = client.post(
        "/reservations", json={"amenity_id": amenidad["id"], "fecha_inicio": _en(1).isoformat(), "fecha_fin": _en(1.1).isoformat()}
    ).json()

    ahora_mas_2_dias = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2)  # ya pasó fecha_inicio
    async with client.db_session_factory() as db:
        resultado = await process_reservation_timeouts(db, ahora_mas_2_dias)

    assert resultado == {"rechazadas": 0, "expiradas": 1}
    _como("admin")
    assert client.get(f"/reservations/{reserva['id']}").json()["estado"] == "expirada"


def test_get_unknown_reservation_404(client):
    response = client.get(f"/reservations/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_requests_for_the_same_slot_are_serialized(client):
    """
    F2-20: dos solicitudes SIMULTÁNEAS (no una después de otra) para el
    mismo horario de la misma amenidad. Antes del candado de F2-20 en
    reservation_service.create_reservation(), esto se comprobó de forma
    empírica y SÍ producía dos reservaciones traslapadas — ambas peticiones
    pasaban la validación antes de que cualquiera hiciera commit. Con el
    candado, exactamente una debe tener éxito.
    """
    prop_a = client.post("/properties", json={"identificador": "Casa 1"}).json()
    prop_b = client.post("/properties", json={"identificador": "Casa 2"}).json()
    amenidad = _crear_amenidad(client)

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    inicio = ahora + timedelta(days=5)
    fin = inicio + timedelta(hours=2)

    async def intentar(property_id: str):
        async with client.db_session_factory() as db:
            try:
                reserva = await create_reservation(db, uuid.UUID(amenidad["id"]), uuid.UUID(property_id), inicio, fin, ahora)
                return ("ok", reserva.id)
            except ReservaInvalida as exc:
                return ("rechazada", exc.motivo)

    resultados = await asyncio.gather(intentar(prop_a["id"]), intentar(prop_b["id"]))

    exitosas = [r for r in resultados if r[0] == "ok"]
    rechazadas = [r for r in resultados if r[0] == "rechazada"]
    assert len(exitosas) == 1
    assert len(rechazadas) == 1
    assert rechazadas[0][1] == "horario_ocupado"

    _como("admin")
    reservas_en_bd = client.get("/reservations").json()
    assert len(reservas_en_bd) == 1


@pytest.mark.asyncio
async def test_concurrent_approve_and_reject_are_serialized(client):
    """
    Revisión de code-review (finding #1): resolve_reservation() no tenía
    ningún candado, a diferencia de create_reservation() — dos resoluciones
    simultáneas de la MISMA reservación podían pisarse. Igual que la prueba
    de doble-booking, esta ejercita el candado real con asyncio.gather(),
    no solo llamadas secuenciales.
    """
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client)

    _como("residente", property_id=prop["id"])
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    inicio = ahora + timedelta(days=5)
    fin = inicio + timedelta(hours=2)

    async def _crear():
        async with client.db_session_factory() as db:
            return await create_reservation(db, uuid.UUID(amenidad["id"]), uuid.UUID(prop["id"]), inicio, fin, ahora)

    reserva = await _crear()

    async def intentar(aprobar: bool):
        async with client.db_session_factory() as db:
            resultado = await resolve_reservation(db, reserva.id, uuid.UUID(str(uuid.uuid4())), aprobar)
            return resultado.estado.value if resultado is not None else None

    resultados = await asyncio.gather(intentar(True), intentar(False))

    exitosos = [r for r in resultados if r is not None]
    assert len(exitosos) == 1  # solo una de las dos resoluciones debió aplicarse
    assert exitosos[0] in {"aprobada", "rechazada"}


@pytest.mark.asyncio
async def test_timeout_prefers_expirada_when_both_conditions_are_true(client):
    """
    Revisión de code-review (finding #8): antes, si el plazo de respuesta Y
    la fecha_inicio ya habían pasado a la vez (job atrasado), siempre ganaba
    "rechazada" — contradiciendo el propio docstring de la función, que dice
    que fecha_inicio pasada gana "ni siquiera venciendo el periodo_limite_horas".
    """
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    amenidad = _crear_amenidad(client, periodo_limite_horas=4)

    _como("residente", property_id=prop["id"])
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    inicio = ahora + timedelta(hours=6)  # fecha_inicio pasa a las 6h
    fin = inicio + timedelta(hours=1)

    async with client.db_session_factory() as db:
        reserva = await create_reservation(db, uuid.UUID(amenidad["id"]), uuid.UUID(prop["id"]), inicio, fin, ahora)

    # El job corre en la hora 7: tanto el plazo de respuesta (4h) como
    # fecha_inicio (6h) ya pasaron — debe ganar "expirada".
    ahora_mas_7h = ahora + timedelta(hours=7)
    async with client.db_session_factory() as db:
        resultado = await process_reservation_timeouts(db, ahora_mas_7h)

    assert resultado == {"rechazadas": 0, "expiradas": 1}
    _como("admin")
    assert client.get(f"/reservations/{reserva.id}").json()["estado"] == "expirada"
