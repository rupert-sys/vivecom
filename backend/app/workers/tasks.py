"""
Job periódico: recorre TODOS los tenants y genera los cargos del mes para
cada uno. Celery es síncrono por naturaleza, así que cada tenant se procesa
dentro de su propio asyncio.run() — no se comparte una sola corrida de event
loop entre tenants, para que un error en uno no tumbe a los demás.
"""

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import tenant_session
from app.models.tenant import Tenant
from app.services.announcement_service import send_announcement_notifications
from app.services.fee_charge_service import apply_late_surcharges, generate_charges_for_period
from app.services.notification_providers.twilio_provider import TwilioProvider
from app.services.package_notification_service import send_package_notifications
from app.services.poll_service import process_poll_closures
from app.services.reminder_service import send_payment_confirmations, send_payment_reminders
from app.services.reservation_service import process_reservation_timeouts
from app.services.payment_agreement_service import procesar_acuerdos
from app.workers.celery_app import celery_app

_notification_provider = TwilioProvider(
    account_sid=settings.twilio_account_sid,
    auth_token=settings.twilio_auth_token,
    whatsapp_from=settings.twilio_whatsapp_from,
    sms_from=settings.twilio_sms_from,
)


async def _generate_for_all_tenants(periodo: date) -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                nuevos = await generate_charges_for_period(db, periodo)
            resultados[tenant.schema_name] = len(nuevos)
        except Exception as exc:  # noqa: BLE001 — un tenant con error no debe tumbar a los demás
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _apply_surcharges_for_all_tenants(hoy: date) -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                afectados = await apply_late_surcharges(db, hoy)
            resultados[tenant.schema_name] = len(afectados)
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _send_reminders_for_all_tenants(hoy: date) -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                enviados = await send_payment_reminders(db, _notification_provider, hoy)
            resultados[tenant.schema_name] = enviados
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _send_confirmations_for_all_tenants() -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                enviados = await send_payment_confirmations(db, _notification_provider)
            resultados[tenant.schema_name] = enviados
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _send_announcement_notifications_for_all_tenants() -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                ahora = datetime.now(timezone.utc).replace(tzinfo=None)
                enviados = await send_announcement_notifications(db, _notification_provider, ahora)
            resultados[tenant.schema_name] = enviados
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _send_package_notifications_for_all_tenants() -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                enviados = await send_package_notifications(db, _notification_provider)
            resultados[tenant.schema_name] = enviados
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _process_poll_closures_for_all_tenants(hoy: date) -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                resultado = await process_poll_closures(db, _notification_provider, hoy)
            resultados[tenant.schema_name] = resultado["reactivadas"]
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _process_reservation_timeouts_for_all_tenants() -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                ahora = datetime.now(timezone.utc).replace(tzinfo=None)
                resultado = await process_reservation_timeouts(db, ahora)
            resultados[tenant.schema_name] = resultado["rechazadas"] + resultado["expiradas"]
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


async def _process_agreements_for_all_tenants(hoy: date) -> dict[str, int]:
    # statement_cache_size=0 en ambas capas: sin esto, una conexión de este pool que ya sirvió a un
    # tenant en esta misma corrida cachea el plan preparado atado al tipo ENUM de SU schema, y truena
    # con CannotCoerceError al reusarse para el siguiente tenant (mismo motivo documentado en el
    # engine global de app/core/database.py, que este engine local no heredaba).
    engine = create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resultados: dict[str, int] = {}
    async with session_factory() as control_db:
        tenants = (await control_db.execute(select(Tenant))).scalars().all()

    for tenant in tenants:
        try:
            async with tenant_session(tenant.schema_name, session_factory) as db:
                resultado = await procesar_acuerdos(db, hoy)
            resultados[tenant.schema_name] = resultado["cumplidos"] + resultado["incumplidos"]
        except Exception as exc:  # noqa: BLE001
            resultados[tenant.schema_name] = f"error: {exc}"

    await engine.dispose()
    return resultados


@celery_app.task(name="app.workers.tasks.generate_monthly_charges_task")
def generate_monthly_charges_task() -> dict[str, int]:
    periodo = date.today().replace(day=1)
    return asyncio.run(_generate_for_all_tenants(periodo))


@celery_app.task(name="app.workers.tasks.apply_late_surcharges_task")
def apply_late_surcharges_task() -> dict[str, int]:
    return asyncio.run(_apply_surcharges_for_all_tenants(date.today()))


@celery_app.task(name="app.workers.tasks.send_payment_reminders_task")
def send_payment_reminders_task() -> dict[str, int]:
    return asyncio.run(_send_reminders_for_all_tenants(date.today()))


@celery_app.task(name="app.workers.tasks.send_payment_confirmations_task")
def send_payment_confirmations_task() -> dict[str, int]:
    return asyncio.run(_send_confirmations_for_all_tenants())


@celery_app.task(name="app.workers.tasks.send_announcement_notifications_task")
def send_announcement_notifications_task() -> dict[str, int]:
    return asyncio.run(_send_announcement_notifications_for_all_tenants())


@celery_app.task(name="app.workers.tasks.send_package_notifications_task")
def send_package_notifications_task() -> dict[str, int]:
    return asyncio.run(_send_package_notifications_for_all_tenants())


@celery_app.task(name="app.workers.tasks.process_poll_closures_task")
def process_poll_closures_task() -> dict[str, int]:
    return asyncio.run(_process_poll_closures_for_all_tenants(date.today()))


@celery_app.task(name="app.workers.tasks.process_reservation_timeouts_task")
def process_reservation_timeouts_task() -> dict[str, int]:
    return asyncio.run(_process_reservation_timeouts_for_all_tenants())


@celery_app.task(name="app.workers.tasks.process_payment_agreements_task")
def process_payment_agreements_task() -> dict[str, int]:
    return asyncio.run(_process_agreements_for_all_tenants(date.today()))
