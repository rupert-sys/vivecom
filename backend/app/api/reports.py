import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.user import Rol
from app.schemas.reports import CollectionsSummary
from app.services.collections_summary_service import get_collections_summary
from app.services.export_service import (
    build_account_statements_excel, build_accounting_entries_excel, build_budget_report_excel, build_expenses_excel,
)

router = APIRouter(prefix="/reports", tags=["reports"])

tesorero_only = [Depends(require_roles(Rol.tesorero, Rol.admin))]

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx_response(contenido: bytes, filename: str) -> Response:
    return Response(
        content=contenido,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/collections-summary", response_model=CollectionsSummary, dependencies=tesorero_only)
async def collections_summary(
    periodo: date | None = None, property_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_tenant_db)
):
    """F1-21: cobrado vs. pendiente para el dashboard financiero del panel admin, filtrable por vivienda y periodo."""
    return await get_collections_summary(db, periodo, property_id)


@router.get("/account-statements/export", dependencies=tesorero_only)
async def export_account_statements(property_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_tenant_db)):
    contenido = await build_account_statements_excel(db, property_id)
    return _xlsx_response(contenido, "estados_de_cuenta.xlsx")


@router.get("/expenses/export", dependencies=tesorero_only)
async def export_expenses(
    desde: date | None = None,
    hasta: date | None = None,
    categoria: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
):
    contenido = await build_expenses_excel(db, desde, hasta, categoria)
    return _xlsx_response(contenido, "gastos.xlsx")


@router.get("/budget/export", dependencies=tesorero_only)
async def export_budget_report(periodo: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    periodo_objetivo = periodo or date.today().replace(day=1)
    contenido = await build_budget_report_excel(db, periodo_objetivo)
    return _xlsx_response(contenido, "presupuesto_vs_real.xlsx")


@router.get("/accounting-entries/export", dependencies=tesorero_only)
async def export_accounting_entries(
    desde: date | None = None, hasta: date | None = None, db: AsyncSession = Depends(get_tenant_db)
):
    """F3-01: movimientos (ingresos/egresos) para que el contador los importe a su propio software."""
    contenido = await build_accounting_entries_excel(db, desde, hasta)
    return _xlsx_response(contenido, "movimientos_contables.xlsx")
