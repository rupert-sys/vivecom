from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.budget import Budget
from app.models.user import Rol
from app.schemas.budget import BudgetComparison, BudgetCreate, BudgetRead
from app.services.budget_service import get_budget_vs_actual

router = APIRouter(prefix="/budgets", tags=["budgets"])

tesorero_only = [Depends(require_roles(Rol.tesorero))]


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED, dependencies=tesorero_only)
async def create_budget(payload: BudgetCreate, db: AsyncSession = Depends(get_tenant_db)):
    budget = Budget(
        categoria=payload.categoria, periodicidad=payload.periodicidad, periodo=payload.periodo,
        monto_planeado=payload.monto_planeado,
    )
    db.add(budget)
    await db.commit()
    return budget


@router.get("", response_model=list[BudgetRead])
async def list_budgets(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Budget).order_by(Budget.periodo.desc()))
    return result.scalars().all()


@router.get("/report", response_model=list[BudgetComparison])
async def budget_vs_actual_report(periodo: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """
    HU-A10: compara planeado (Budget) vs. real (suma de Expense) por
    categoría, para el mes/año pedido.
    """
    periodo_objetivo = periodo or date.today().replace(day=1)
    comparaciones = await get_budget_vs_actual(db, periodo_objetivo)
    return [
        BudgetComparison(
            categoria=c.categoria, periodicidad=c.periodicidad, monto_planeado=c.monto_planeado,
            monto_real=c.monto_real,
        )
        for c in comparaciones
    ]
