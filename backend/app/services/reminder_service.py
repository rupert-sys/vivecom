"""
Recordatorios y confirmaciones de pago (F1-13, depende de F1-04 y F1-12).

Dos jobs independientes, ambos idempotentes a su manera:

- send_payment_reminders(): recorre los FeeCharge pendientes/vencidos cuyo
  periodo ya empezó ("desde el día 1 del mes", alcance) y manda un
  recordatorio a los residentes de esa vivienda — como mucho una vez por
  día (recordatorio_enviado_en), pero se REPITE cada día mientras el cargo
  siga sin pagarse, tal como pide el alcance ("hasta que se registre el
  pago"). No usa el estado "vencido" como filtro especial: el recargo es un
  tema aparte (F1-04), el recordatorio aplica igual antes y después.

- send_payment_confirmations(): recorre los FeeCharge que ya están pagados
  pero cuya confirmación no se ha mandado (confirmacion_enviada=False) y
  manda un solo mensaje. Deliberadamente separado de la lógica de
  conciliación (F1-07/F1-09/F1-10): un cargo puede pagarse por un depósito
  directo, saldo a favor, pago anticipado o resolución manual del tesorero,
  y no queremos que cada uno de esos caminos tenga que saber de WhatsApp/SMS
  — esta función barre el resultado, sin importar cuál de ellos lo causó.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.resident import Resident, ResidentProperty
from app.services.notification_providers.base import NotificationProvider

_MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _periodo_legible(periodo: date) -> str:
    return f"{_MESES_ES[periodo.month - 1]} {periodo.year}"


def _mensaje_recordatorio(cargo: FeeCharge) -> str:
    total = float(cargo.monto_base) + float(cargo.recargo_aplicado)
    return (
        f"Vivecom: tienes un cargo pendiente de ${total:,.2f} MXN de "
        f"{_periodo_legible(cargo.periodo)}. Recuerda transferir usando tu referencia de pago."
    )


def _mensaje_confirmacion(cargo: FeeCharge) -> str:
    total = float(cargo.monto_base) + float(cargo.recargo_aplicado)
    return f"Vivecom: recibimos tu pago de ${total:,.2f} MXN de {_periodo_legible(cargo.periodo)}. ¡Gracias!"


async def _telefonos_de_vivienda(db: AsyncSession, property_id) -> list[str]:
    result = await db.execute(
        select(Resident.telefono)
        .join(ResidentProperty, ResidentProperty.resident_id == Resident.id)
        .where(ResidentProperty.property_id == property_id)
    )
    return [telefono for telefono in result.scalars().all() if telefono]


async def send_payment_reminders(db: AsyncSession, provider: NotificationProvider, hoy: date) -> int:
    result = await db.execute(
        select(FeeCharge).where(
            FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido]),
            FeeCharge.periodo <= hoy,
        )
    )
    candidatos = [cargo for cargo in result.scalars().all() if cargo.recordatorio_enviado_en != hoy]

    for cargo in candidatos:
        mensaje = _mensaje_recordatorio(cargo)
        for telefono in await _telefonos_de_vivienda(db, cargo.property_id):
            await provider.send(telefono, mensaje)
        cargo.recordatorio_enviado_en = hoy

    if candidatos:
        await db.commit()
    return len(candidatos)


async def send_payment_confirmations(db: AsyncSession, provider: NotificationProvider) -> int:
    """
    Revisión: antes se marcaba confirmacion_enviada=True sin fijarse si
    provider.send() de verdad tuvo éxito — a diferencia de los recordatorios
    (que se reintentan solos al día siguiente), esta confirmación no tiene
    ninguna otra oportunidad de reintento una vez marcada, así que un envío
    fallido (Twilio caído, número inválido) quedaba "confirmado" para
    siempre sin haber llegado nunca. Ahora solo se marca si todos los envíos
    intentados tuvieron éxito (o si no había a quién avisar) — si alguno
    falla, el cargo se queda sin marcar para que la siguiente corrida lo
    reintente.
    """
    result = await db.execute(
        select(FeeCharge).where(FeeCharge.estado == EstadoCargo.pagado, FeeCharge.confirmacion_enviada.is_(False))
    )
    candidatos = result.scalars().all()

    confirmados = 0
    for cargo in candidatos:
        mensaje = _mensaje_confirmacion(cargo)
        telefonos = await _telefonos_de_vivienda(db, cargo.property_id)
        resultados = [await provider.send(telefono, mensaje) for telefono in telefonos]
        if all(resultados):
            cargo.confirmacion_enviada = True
            confirmados += 1

    if confirmados:
        await db.commit()
    return confirmados
