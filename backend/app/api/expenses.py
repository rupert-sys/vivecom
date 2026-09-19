import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.expense import Expense
from app.models.user import Rol
from app.schemas.expense import ExpenseCreate, ExpenseRead, FinancialSummary
from app.services.financial_summary_service import get_financial_summary
from app.services.reglamento_service import get_reglamento

router = APIRouter(prefix="/expenses", tags=["expenses"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_expense(payload: ExpenseCreate, db: AsyncSession = Depends(get_tenant_db)):
    """
    Reglamento Art. 8: un gasto programado o extraordinario que supere el
    umbral del condominio (Arequipa: $10,000) solo se registra con la
    aprobación de la asamblea y las cotizaciones mínimas de proveedores
    distintos. Sin umbral configurado no se exige nada (comportamiento previo).
    """
    reglamento = await get_reglamento(db)
    umbral = reglamento.gasto_umbral_asamblea
    if payload.tipo != "operativo" and umbral is not None and payload.monto > umbral:
        if not payload.aprobado_en_asamblea:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Un gasto {payload.tipo} mayor a ${umbral:,.2f} requiere aprobación de la asamblea.",
            )
        proveedores = {c.proveedor.strip().lower() for c in payload.cotizaciones}
        if len(proveedores) < reglamento.cotizaciones_minimas:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Se requieren al menos {reglamento.cotizaciones_minimas} cotizaciones de proveedores distintos "
                f"(hay {len(proveedores)}).",
            )

    expense = Expense(
        categoria=payload.categoria, monto=payload.monto, comprobante_url=payload.comprobante_url,
        fecha=payload.fecha, tipo=payload.tipo, aprobado_en_asamblea=payload.aprobado_en_asamblea,
        acta_referencia=payload.acta_referencia, tipo_comprobante=payload.tipo_comprobante,
        cotizaciones=[c.model_dump() for c in payload.cotizaciones] or None,
    )
    db.add(expense)
    await db.commit()
    return expense


@router.get("/summary", response_model=FinancialSummary)
async def expenses_summary(
    desde: date | None = None, hasta: date | None = None, db: AsyncSession = Depends(get_tenant_db)
):
    """
    Ingresos, gastos y saldo del condominio en un rango. Lectura abierta a
    cualquier rol autenticado por la misma razón que la lista de gastos
    (HU-A12): el reglamento obliga a rendir cuentas a todos los condóminos.
    """
    return await get_financial_summary(db, desde, hasta)


@router.get("", response_model=list[ExpenseRead])
async def list_expenses(
    desde: date | None = None,
    hasta: date | None = None,
    categoria: str | None = None,
    tipo: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Lectura abierta a cualquier rol autenticado del tenant — HU-A12: la
    transparencia de gastos es para cualquier residente, no solo el admin.
    """
    query = select(Expense).order_by(Expense.fecha.desc())
    if desde is not None:
        query = query.where(Expense.fecha >= desde)
    if hasta is not None:
        query = query.where(Expense.fecha <= hasta)
    if categoria is not None:
        query = query.where(Expense.categoria == categoria)
    if tipo is not None:
        query = query.where(Expense.tipo == tipo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{expense_id}", response_model=ExpenseRead)
async def get_expense(expense_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    expense = await db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gasto no encontrado")
    return expense
