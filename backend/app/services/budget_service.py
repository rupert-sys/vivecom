"""
Presupuesto vs. real (F1-16, HU-A10): "El reporte compara planeado vs. real
por categoría y periodo." Filtra en Python en vez de con funciones de fecha
específicas del motor (EXTRACT/strftime): el proyecto corre sobre SQLite en
pruebas y Postgres en producción, y esas funciones no son portables entre
los dos — la tabla de presupuestos no es lo bastante grande como para que
esto importe.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, PeriodicidadPresupuesto
from app.models.expense import Expense


@dataclass
class ComparacionCategoria:
    categoria: str
    periodicidad: PeriodicidadPresupuesto
    monto_planeado: float
    monto_real: float


def _rango_del_ciclo(budget: Budget) -> tuple[date, date]:
    """[inicio, fin) del ciclo que cubre este presupuesto."""
    if budget.periodicidad == PeriodicidadPresupuesto.anual:
        return date(budget.periodo.year, 1, 1), date(budget.periodo.year + 1, 1, 1)
    inicio = date(budget.periodo.year, budget.periodo.month, 1)
    if budget.periodo.month == 12:
        return inicio, date(budget.periodo.year + 1, 1, 1)
    return inicio, date(budget.periodo.year, budget.periodo.month + 1, 1)


async def get_budget_vs_actual(db: AsyncSession, periodo: date) -> list[ComparacionCategoria]:
    """
    Presupuestos vigentes para `periodo`: los mensuales cuyo periodo es
    exactamente ese mes, y los anuales cuyo año coincide.
    """
    todos = (await db.execute(select(Budget))).scalars().all()
    vigentes = [
        budget
        for budget in todos
        if (
            budget.periodicidad == PeriodicidadPresupuesto.mensual
            and budget.periodo == date(periodo.year, periodo.month, 1)
        )
        or (budget.periodicidad == PeriodicidadPresupuesto.anual and budget.periodo.year == periodo.year)
    ]

    comparaciones = []
    for budget in vigentes:
        inicio, fin = _rango_del_ciclo(budget)
        result = await db.execute(
            select(func.sum(Expense.monto)).where(
                Expense.categoria == budget.categoria, Expense.fecha >= inicio, Expense.fecha < fin
            )
        )
        monto_real = float(result.scalar() or 0)
        comparaciones.append(
            ComparacionCategoria(
                categoria=budget.categoria,
                periodicidad=budget.periodicidad,
                monto_planeado=float(budget.monto_planeado),
                monto_real=monto_real,
            )
        )
    return comparaciones
