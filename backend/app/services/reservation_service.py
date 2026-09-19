"""
F2-16 (HU-C06, reservación de amenidades con bloqueo anti doble-booking) y
F2-17 (HU-C07, flujo de aprobación con rechazo automático por tiempo).
"""

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import advertir_si_with_for_update_es_no_op
from app.models.amenity import Amenity, AmenityApprover
from app.models.reservation import EstadoReserva, Reservation
from app.models.resident import Resident
from app.models.user import UserAccount
from app.services.reglamento_service import TZ_CONDOMINIO, get_reglamento, vivienda_en_mora


class ReservaInvalida(Exception):
    def __init__(self, motivo: str, detalle: str | None = None):
        self.motivo = motivo
        # Mensaje ya redactado para el residente cuando el motivo lleva datos
        # (ej. cuántos días de anticipación pide esta amenidad).
        self.detalle = detalle
        super().__init__(motivo)


def max_simultaneas(reservaciones, inicio: datetime, fin: datetime) -> int:
    """
    Cuántas reservaciones coinciden AL MISMO TIEMPO como máximo dentro de
    [inicio, fin). Dos reservaciones consecutivas (una termina cuando la otra
    empieza) no cuentan como simultáneas.
    """
    eventos = []
    for reserva in reservaciones:
        eventos.append((max(reserva.fecha_inicio, inicio), 1))
        eventos.append((min(reserva.fecha_fin, fin), -1))
    eventos.sort(key=lambda e: (e[0], e[1]))  # -1 antes que +1 en el mismo instante
    actual = maximo = 0
    for _, delta in eventos:
        actual += delta
        maximo = max(maximo, actual)
    return maximo


def _a_local(naive_utc: datetime) -> datetime:
    """Los datetimes del proyecto son UTC 'naive' — las reglas del reglamento se evalúan en hora local."""
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(TZ_CONDOMINIO)


def _formato_hora(hora: time) -> str:
    return f"{hora:%H:%M}"


def validar_reglas_de_la_amenidad(amenidad: Amenity, fecha_inicio: datetime, fecha_fin: datetime, ahora: datetime) -> None:
    """
    Reglas del reglamento para reservar esta amenidad (Condominio Arequipa,
    Art. 2 III-V): anticipación mínima, días y horario permitidos, horario
    máximo de uso y duración. Todas evalúan en hora LOCAL del condominio: a las
    11pm en México ya es "mañana" en UTC. Las reglas por defecto (0 días, sin
    ventana, sin tope) no restringen nada — una amenidad sin configurar se
    comporta como antes.
    """
    inicio, fin, hoy = _a_local(fecha_inicio), _a_local(fecha_fin), _a_local(ahora).date()

    if amenidad.dias_anticipacion_minimos:
        dias = (inicio.date() - hoy).days
        if dias < amenidad.dias_anticipacion_minimos:
            raise ReservaInvalida(
                "anticipacion_insuficiente",
                f"{amenidad.nombre} se debe solicitar con al menos {amenidad.dias_anticipacion_minimos} días de "
                f"anticipación (faltan {dias} para esa fecha)",
            )

    if amenidad.dias_semana_permitidos:
        permitidos = {int(d) for d in amenidad.dias_semana_permitidos.split(",") if d.strip() != ""}
        dia, ultimo = inicio.date(), (fin - timedelta(microseconds=1)).date()
        while dia <= ultimo:
            if dia.weekday() not in permitidos:
                nombres = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
                validos = ", ".join(nombres[d] for d in sorted(permitidos))
                raise ReservaInvalida(
                    "dia_no_permitido", f"{amenidad.nombre} solo se puede usar: {validos}"
                )
            dia += timedelta(days=1)

    if amenidad.hora_inicio_permitida and inicio.timetz().replace(tzinfo=None) < amenidad.hora_inicio_permitida:
        raise ReservaInvalida(
            "fuera_de_horario",
            f"{amenidad.nombre} se puede usar a partir de las {_formato_hora(amenidad.hora_inicio_permitida)}",
        )

    if amenidad.hora_fin_maxima:
        # El primer momento, a partir del inicio, en que se llega a la hora
        # máxima: "hasta la 01:00 am" para un evento que empieza a las 15:00
        # significa la 01:00 del día siguiente.
        limite = inicio.replace(
            hour=amenidad.hora_fin_maxima.hour, minute=amenidad.hora_fin_maxima.minute, second=0, microsecond=0
        )
        if limite <= inicio:
            limite += timedelta(days=1)
        if fin > limite:
            raise ReservaInvalida(
                "fuera_de_horario",
                f"El horario máximo de uso de {amenidad.nombre} es hasta las {_formato_hora(amenidad.hora_fin_maxima)}",
            )

    if amenidad.max_duracion_horas and (fecha_fin - fecha_inicio) > timedelta(hours=amenidad.max_duracion_horas):
        raise ReservaInvalida(
            "duracion_excedida",
            f"{amenidad.nombre} se puede reservar por un máximo de {amenidad.max_duracion_horas} horas",
        )


# F2-20 (QA de concurrencia): sin esto, dos solicitudes simultáneas para el
# mismo horario pueden AMBAS pasar la validación de traslape antes de que
# cualquiera de las dos haga commit — se comprobó de forma empírica con
# asyncio.gather() contra este mismo código antes de agregar el candado, y
# sí se producía un doble-booking real. Dos capas, cada una cubre lo que la
# otra no puede:
#   1. Este asyncio.Lock por amenidad cierra la carrera DENTRO de un mismo
#      proceso — verificado con una prueba real (test_reservations.py::
#      test_concurrent_requests_for_the_same_slot_are_serialized) que sin
#      el candado falla de forma reproducible.
#   2. with_for_update() en la fila de Amenity (ver abajo) es la protección
#      real entre procesos/workers distintos en Postgres — bloquea al
#      segundo proceso hasta que el primero comitea. No se pudo verificar
#      de punta a punta aquí: SQLAlchemy compila with_for_update() como
#      no-op silencioso en SQLite (confirmado), así que en las pruebas de
#      esta sesión esa capa no se ejercita — sí es el comportamiento
#      documentado de Postgres, pero queda pendiente de confirmar contra un
#      Postgres real antes de confiar en ella entre varios workers.
_locks_por_amenidad: dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)
_locks_por_reserva: dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


async def create_reservation(
    db: AsyncSession, amenity_id: uuid.UUID, property_id: uuid.UUID, fecha_inicio: datetime, fecha_fin: datetime,
    ahora: datetime,
) -> Reservation:
    """
    HU-C06: el alcance dice "mínimo 2 días de anticipación, salvo que el
    horario siga disponible más cerca de la fecha" — en la práctica eso
    significa que la ÚNICA restricción real es la disponibilidad, no un
    conteo de días: si el horario está libre, se puede reservar con
    cualquier anticipación. RESERVACION_ANTICIPACION_MINIMA_DIAS se expone
    como referencia informativa (GET /reservations/global-rules), no como
    regla de rechazo aquí — inventar ese rechazo contradiría la propia
    excepción que describe el alcance.

    Sí se bloquea el doble-booking: dos reservaciones de la misma amenidad
    no pueden traslaparse mientras ninguna esté descartada (una rechazada o
    expirada ya no aparta el horario). Ver F2-20 arriba sobre por qué esto
    necesita un candado explícito, no solo la consulta de traslape.
    """
    if fecha_fin <= fecha_inicio:
        raise ReservaInvalida("rango_invalido")
    if fecha_inicio < ahora:
        raise ReservaInvalida("fecha_pasada")

    amenidad = await db.get(Amenity, amenity_id)
    if amenidad is None:
        raise ReservaInvalida("amenidad_inexistente")
    validar_reglas_de_la_amenidad(amenidad, fecha_inicio, fecha_fin, ahora)

    # Reglamento (Arequipa Art. 2 VIII y Art. 21 II): las viviendas con adeudo
    # no pueden usar las áreas comunes, ni siquiera con carta compromiso.
    reglamento = await get_reglamento(db)
    if reglamento.morosos_sin_areas_comunes and await vivienda_en_mora(
        db, property_id, _a_local(ahora).date(), reglamento
    ):
        raise ReservaInvalida(
            "moroso",
            "Tu vivienda tiene cuotas vencidas: según el reglamento no puede usar las áreas comunes "
            "hasta que regularices tu pago",
        )

    async with _locks_por_amenidad[amenity_id]:
        # with_for_update(): no cambia nada en SQLite (no-op), pero en
        # Postgres bloquea esta fila hasta el commit — el candado real
        # entre procesos. Ver nota de F2-20 arriba.
        advertir_si_with_for_update_es_no_op(db, "reservation_service.create_reservation")
        await db.execute(select(Amenity).where(Amenity.id == amenity_id).with_for_update())

        traslapes = (
            await db.execute(
                select(Reservation).where(
                    Reservation.amenity_id == amenity_id,
                    Reservation.estado.in_([EstadoReserva.pendiente, EstadoReserva.aprobada]),
                    Reservation.fecha_inicio < fecha_fin,
                    Reservation.fecha_fin > fecha_inicio,
                )
            )
        ).scalars().all()
        # capacidad > 1 (ej. 7 cajones de estacionamiento): el horario solo está
        # ocupado cuando ya no queda lugar en ALGÚN momento del rango pedido.
        # Con capacidad 1 (lo normal) es el doble-booking de siempre.
        if max_simultaneas(traslapes, fecha_inicio, fecha_fin) >= amenidad.capacidad:
            raise ReservaInvalida("horario_ocupado")

        reserva = Reservation(
            amenity_id=amenity_id, property_id=property_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
            solicitada_en=ahora, cuota=amenidad.cuota or 0, cuota_pagada=False,
        )
        db.add(reserva)
        await db.commit()
        return reserva


async def is_amenity_approver(db: AsyncSession, amenity_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(AmenityApprover).where(AmenityApprover.amenity_id == amenity_id, AmenityApprover.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


async def resolve_reservation(
    db: AsyncSession, reservation_id: uuid.UUID, aprobador_id: uuid.UUID, aprobar: bool
) -> Reservation | None:
    """
    None si la reservación no existe o ya no está pendiente (ya se resolvió,
    se rechazó por tiempo, o expiró).

    Revisión post-F2-20: esta función tenía la MISMA carrera que
    create_reservation (dos aprobadores resolviendo la misma reservación a
    la vez) sin ninguna de las dos capas de protección — se corrige con el
    mismo patrón: candado en memoria por reservación (probado de verdad) +
    with_for_update() sobre la fila (protección entre procesos en Postgres,
    con la misma limitación ya documentada arriba: no verificable aquí).
    """
    async with _locks_por_reserva[reservation_id]:
        advertir_si_with_for_update_es_no_op(db, "reservation_service.resolve_reservation")
        reserva = (
            await db.execute(select(Reservation).where(Reservation.id == reservation_id).with_for_update())
        ).scalar_one_or_none()
        if reserva is None or reserva.estado != EstadoReserva.pendiente:
            return None

        reserva.estado = EstadoReserva.aprobada if aprobar else EstadoReserva.rechazada
        reserva.aprobador_id = aprobador_id
        await db.commit()
        return reserva


async def telefonos_de_aprobadores(db: AsyncSession, amenity_id: uuid.UUID) -> list[str]:
    """HU-C07: a quién avisar cuando se solicita una reservación."""
    user_ids = (
        await db.execute(select(AmenityApprover.user_id).where(AmenityApprover.amenity_id == amenity_id))
    ).scalars().all()
    if not user_ids:
        return []

    resident_ids = (
        await db.execute(
            select(UserAccount.resident_id).where(UserAccount.id.in_(user_ids), UserAccount.resident_id.is_not(None))
        )
    ).scalars().all()
    if not resident_ids:
        return []

    result = await db.execute(select(Resident.telefono).where(Resident.id.in_(resident_ids)))
    return [telefono for telefono in result.scalars().all() if telefono]


async def telefonos_de_vivienda(db: AsyncSession, property_id: uuid.UUID) -> list[str]:
    from app.models.resident import ResidentProperty

    result = await db.execute(
        select(Resident.telefono)
        .join(ResidentProperty, ResidentProperty.resident_id == Resident.id)
        .where(ResidentProperty.property_id == property_id)
    )
    return [telefono for telefono in result.scalars().all() if telefono]


async def process_reservation_timeouts(db: AsyncSession, ahora: datetime) -> dict[str, int]:
    """
    HU-C07: rechazo automático si nadie responde dentro del
    periodo_limite_horas de la amenidad, contado desde solicitada_en.
    HU-C06: si el bloque de tiempo reservado (fecha_inicio) ya pasó y la
    reservación sigue pendiente — nadie respondió, ni siquiera venciendo el
    periodo_limite_horas, o ese periodo era más largo que la ventana misma
    — se marca expirada en vez de rechazada, para distinguir "nadie
    contestó a tiempo" de "el evento ya pasó sin resolverse".
    """
    pendientes = (
        await db.execute(select(Reservation).where(Reservation.estado == EstadoReserva.pendiente))
    ).scalars().all()

    rechazadas = 0
    expiradas = 0
    for reserva in pendientes:
        amenidad = await db.get(Amenity, reserva.amenity_id)
        limite_respuesta = reserva.solicitada_en + timedelta(hours=amenidad.periodo_limite_horas)

        # Revisión: el orden importa. fecha_inicio se revisa PRIMERO — si el
        # bloque de tiempo reservado ya pasó, es "expirada" sin importar que
        # el plazo de respuesta también haya vencido (así lo dice el
        # docstring de esta función: "ni siquiera venciendo el
        # periodo_limite_horas"). El orden original revisaba rechazada
        # primero, así que cuando ambas condiciones eran ciertas a la vez
        # (job atrasado) siempre ganaba rechazada, contradiciendo lo
        # documentado — no había ninguna prueba que cubriera ese cruce.
        if reserva.fecha_inicio <= ahora:
            reserva.estado = EstadoReserva.expirada
            expiradas += 1
        elif limite_respuesta <= ahora:
            reserva.estado = EstadoReserva.rechazada
            rechazadas += 1

    if pendientes:
        await db.commit()
    return {"rechazadas": rechazadas, "expiradas": expiradas}
