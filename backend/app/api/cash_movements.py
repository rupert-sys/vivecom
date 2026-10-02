import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.cash_movement import CashMovement, Caja, TipoMovimiento
from app.models.user import Rol
from app.schemas.cash_movement import CashBalance, CashMovementCreate, CashMovementRead

router = APIRouter(prefix="/cash-movements", tags=["cash-movements"])

tesorero_only = [Depends(require_roles(Rol.tesorero))]


@router.post("", response_model=CashMovementRead, status_code=status.HTTP_201_CREATED, dependencies=tesorero_only)
async def create_cash_movement(
    payload: CashMovementCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """F0-12: solo tesorería mete/saca dinero de caja chica o caja grande."""
    movimiento = CashMovement(
        caja=payload.caja, tipo=payload.tipo, monto=payload.monto, motivo=payload.motivo.strip(),
        fecha=payload.fecha, registrado_por=uuid.UUID(current_user.user_id),
    )
    db.add(movimiento)
    await db.commit()
    return movimiento


@router.get("/balance", response_model=CashBalance)
async def get_cash_balance(db: AsyncSession = Depends(get_tenant_db)):
    """
    Lectura abierta a cualquier rol autenticado — misma transparencia que el resumen financiero de gastos
    (HU-A12): el reglamento obliga a rendir cuentas a todos los condóminos, el efectivo físico no es distinto.
    """
    result = await db.execute(
        select(
            CashMovement.caja, CashMovement.tipo, func.coalesce(func.sum(CashMovement.monto), 0)
        ).group_by(CashMovement.caja, CashMovement.tipo)
    )
    saldos = {Caja.chica: 0.0, Caja.grande: 0.0}
    for caja, tipo, total in result.all():
        signo = 1 if tipo == TipoMovimiento.ingreso else -1
        saldos[caja] += signo * float(total)
    return CashBalance(chica=saldos[Caja.chica], grande=saldos[Caja.grande])


@router.get("", response_model=list[CashMovementRead])
async def list_cash_movements(
    caja: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Lectura abierta — ver nota de transparencia en get_cash_balance."""
    query = select(CashMovement).order_by(CashMovement.fecha.desc(), CashMovement.id.desc())
    if caja is not None:
        query = query.where(CashMovement.caja == caja)
    if desde is not None:
        query = query.where(CashMovement.fecha >= desde)
    if hasta is not None:
        query = query.where(CashMovement.fecha <= hasta)
    result = await db.execute(query)
    return result.scalars().all()
