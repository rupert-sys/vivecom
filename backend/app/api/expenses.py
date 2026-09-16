import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.expense import Expense
from app.models.user import Rol
from app.schemas.expense import ExpenseCreate, ExpenseRead

router = APIRouter(prefix="/expenses", tags=["expenses"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_expense(payload: ExpenseCreate, db: AsyncSession = Depends(get_tenant_db)):
    expense = Expense(
        categoria=payload.categoria, monto=payload.monto, comprobante_url=payload.comprobante_url,
        fecha=payload.fecha,
    )
    db.add(expense)
    await db.commit()
    return expense


@router.get("", response_model=list[ExpenseRead])
async def list_expenses(
    desde: date | None = None,
    hasta: date | None = None,
    categoria: str | None = None,
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
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{expense_id}", response_model=ExpenseRead)
async def get_expense(expense_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    expense = await db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gasto no encontrado")
    return expense
