from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import control_session
from app.services.deposit_processing_service import TenantNoEncontrado, process_incoming_deposit
from app.services.payment_providers.stp import STPProvider

router = APIRouter(prefix="/payments", tags=["payments"])

_stp_provider = STPProvider(webhook_secret=settings.stp_webhook_secret)


@router.post("/webhook/stp", status_code=status.HTTP_200_OK)
async def stp_webhook(request: Request, control_db: AsyncSession = Depends(control_session)):
    """
    Endpoint público (sin JWT — lo llama STP, no un usuario). La seguridad
    viene de la verificación de firma, no de autenticación de usuario.
    """
    raw_body = await request.body()

    if not _stp_provider.verify_webhook_signature(raw_body, request.headers):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma de webhook inválida")

    payload = await request.json()
    try:
        deposito = _stp_provider.parse_deposit_notification(payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Payload de STP inválido: {exc}")

    try:
        payment = await process_incoming_deposit(deposito, control_db)
    except TenantNoEncontrado as exc:
        # 200 (no 4xx): confirmamos recepción a STP para que no reintente
        # infinitamente, pero registramos el problema para revisión manual.
        return {"status": "no_tenant_matched", "detail": str(exc)}

    return {"status": "processed", "payment_id": str(payment.id), "payment_estado": payment.estado.value}
