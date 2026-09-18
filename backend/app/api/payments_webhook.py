import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import control_session
from app.services.deposit_processing_service import TenantNoEncontrado, process_incoming_deposit
from app.services.payment_providers.stp import STPProvider

router = APIRouter(prefix="/payments", tags=["payments"])

_stp_provider = STPProvider(webhook_secret=settings.stp_webhook_secret)

# F2-21: stp_webhook_secret trae un valor placeholder por default (para no
# tronar el arranque en dev, mismo criterio que sentry_dsn en F1-36) — pero a
# diferencia de Sentry, un secreto de firma sin configurar aquí es "fail
# open": cualquiera que haya leído este repo público conoce el string exacto
# y puede firmar un depósito falso. En producción se rechaza de plano en vez
# de aceptar webhooks firmados con un secreto público y conocido.
_SECRET_SIN_CONFIGURAR = "cambia-esto-en-produccion"

logger = logging.getLogger(__name__)


@router.post("/webhook/stp", status_code=status.HTTP_200_OK)
async def stp_webhook(request: Request, control_db: AsyncSession = Depends(control_session)):
    """
    Endpoint público (sin JWT — lo llama STP, no un usuario). La seguridad
    viene de la verificación de firma, no de autenticación de usuario.
    """
    if settings.environment == "production" and settings.stp_webhook_secret == _SECRET_SIN_CONFIGURAR:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook de STP no configurado")

    raw_body = await request.body()

    if not _stp_provider.verify_webhook_signature(raw_body, request.headers):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma de webhook inválida")

    payload = await request.json()
    try:
        deposito = _stp_provider.parse_deposit_notification(payload)
    except (KeyError, ValueError) as exc:
        # No se regresa el detalle de la excepción al llamador: revelaría
        # nombres de campos internos a quien sea que esté probando el
        # endpoint (público, sin autenticación de usuario).
        logger.warning("Payload de STP inválido: %s", exc)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Payload de STP inválido")

    try:
        payment = await process_incoming_deposit(deposito, control_db)
    except TenantNoEncontrado as exc:
        # 200 (no 4xx): confirmamos recepción a STP para que no reintente
        # infinitamente, pero registramos el problema para revisión manual.
        return {"status": "no_tenant_matched", "detail": str(exc)}

    return {"status": "processed", "payment_id": str(payment.id), "payment_estado": payment.estado.value}
