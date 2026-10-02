import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.core.business_rules import RECARGO_DIA_DEL_MES, RECARGO_PORCENTAJE
from app.core.config import settings
from app.models.fee import Fee
from app.models.fee_charge import FeeCharge
from app.models.user import Rol
from app.schemas.fee import FeeCreate, FeeRead, FeeUpdate
from app.services.fee_charge_service import apply_late_surcharges, generate_charges_for_period
from app.services.notification_providers.twilio_provider import TwilioProvider
from app.services.reminder_service import send_payment_confirmations, send_payment_reminders

router = APIRouter(prefix="/fees", tags=["fees"])

admin_only = [Depends(require_roles(Rol.admin))]

_notification_provider = TwilioProvider(
    account_sid=settings.twilio_account_sid,
    auth_token=settings.twilio_auth_token,
    whatsapp_from=settings.twilio_whatsapp_from,
    sms_from=settings.twilio_sms_from,
    api_base=settings.twilio_api_base,
)


@router.get("/global-rules")
async def get_global_rules():
    """
    Reglas de recargo: son iguales para todos los condominios, no se
    configuran por tenant (ver alcance sección 3.1). Se exponen aquí para
    que el panel admin y la app residente las muestren sin duplicar el valor.
    """
    return {"recargo_porcentaje": RECARGO_PORCENTAJE, "recargo_dia_del_mes": RECARGO_DIA_DEL_MES}


@router.post("", response_model=FeeRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_fee(payload: FeeCreate, db: AsyncSession = Depends(get_tenant_db)):
    fee = Fee(monto=payload.monto, periodicidad=payload.periodicidad, activa_desde=payload.activa_desde)
    db.add(fee)
    await db.commit()
    # Sin refresh(): ver la nota en core/database.py — el search_path transaccional
    # ya no aplica después del commit. `fee` ya tiene todos sus campos en memoria.
    return fee


@router.get("", response_model=list[FeeRead])
async def list_fees(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Fee).order_by(Fee.activa_desde.desc()))
    return result.scalars().all()


@router.get("/{fee_id}", response_model=FeeRead)
async def get_fee(fee_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    fee = await db.get(Fee, fee_id)
    if fee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuración de cuota no encontrada")
    return fee


@router.patch("/{fee_id}", response_model=FeeRead, dependencies=admin_only)
async def update_fee(fee_id: uuid.UUID, payload: FeeUpdate, db: AsyncSession = Depends(get_tenant_db)):
    fee = await db.get(Fee, fee_id)
    if fee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuración de cuota no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fee, field, value)
    await db.commit()
    return fee


@router.delete("/{fee_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
async def delete_fee(fee_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """
    Solo se puede eliminar una cuota que todavía no generó ningún cargo (se dio de alta por error, o su fecha
    aún no llega): borrarla después rompería el histórico de FeeCharge, que queda ligado a ella (fee_id).
    """
    fee = await db.get(Fee, fee_id)
    if fee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuración de cuota no encontrada")
    tiene_cargos = (
        await db.execute(select(FeeCharge.id).where(FeeCharge.fee_id == fee_id).limit(1))
    ).scalar_one_or_none()
    if tiene_cargos is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta cuota ya generó cargos: no se puede eliminar, solo editar."
        )
    await db.delete(fee)
    await db.commit()


@router.post("/generate-charges", dependencies=admin_only)
async def trigger_generate_charges(periodo: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """
    Disparo manual de la generación de cargos (el job periódico real vive en
    app/workers/tasks.py). Útil para pruebas y para que el admin la corra
    bajo demanda. Es idempotente: no duplica cargos ya generados.
    """
    periodo_objetivo = periodo or date.today().replace(day=1)
    nuevos = await generate_charges_for_period(db, periodo_objetivo)
    return {"periodo": periodo_objetivo.isoformat(), "cargos_generados": len(nuevos)}


@router.post("/apply-late-surcharges", dependencies=admin_only)
async def trigger_apply_late_surcharges(hoy: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """
    Disparo manual del recargo por mora (10%, a partir del día 6 de cada
    mes). El job real corre diario vía Celery Beat. Idempotente.
    """
    fecha_referencia = hoy or date.today()
    afectados = await apply_late_surcharges(db, fecha_referencia)
    return {"fecha_referencia": fecha_referencia.isoformat(), "cargos_marcados_vencidos": len(afectados)}


@router.post("/send-reminders", dependencies=admin_only)
async def trigger_send_reminders(hoy: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """
    Disparo manual de recordatorios de pago (F1-13). El job real corre
    diario vía Celery Beat. Idempotente: como mucho un recordatorio por
    cargo por día, aunque se dispare varias veces el mismo día.
    """
    fecha_referencia = hoy or date.today()
    enviados = await send_payment_reminders(db, _notification_provider, fecha_referencia)
    return {"fecha_referencia": fecha_referencia.isoformat(), "recordatorios_enviados": enviados}


@router.post("/send-payment-confirmations", dependencies=admin_only)
async def trigger_send_payment_confirmations(db: AsyncSession = Depends(get_tenant_db)):
    """
    Disparo manual de confirmaciones de pago (F1-13). El job real corre cada
    pocos minutos vía Celery Beat (a diferencia de los recordatorios, aquí sí
    importa que la confirmación llegue pronto). Idempotente: cada cargo se
    confirma una sola vez.
    """
    enviados = await send_payment_confirmations(db, _notification_provider)
    return {"confirmaciones_enviadas": enviados}
