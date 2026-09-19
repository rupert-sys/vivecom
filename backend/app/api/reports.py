import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.user import Rol
from app.models.property import Property
from app.models.tenant import Tenant
from app.schemas.reports import CollectionsSummary, EstatusCobranza
from app.services.collections_summary_service import get_collections_summary
from app.services.financial_summary_service import get_collection_status
from app.services.no_debt_certificate_service import build_no_debt_certificate_pdf
from app.services.reglamento_service import hoy_local
from app.services.statement_service import get_account_statement
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


@router.get("/collection-status", response_model=EstatusCobranza, dependencies=tesorero_only)
async def collection_status(periodo: date | None = None, db: AsyncSession = Depends(get_tenant_db)):
    """Quién ya pagó, quién falta y quién es moroso (por vivienda), con conteos para el resumen del panel."""
    return await get_collection_status(db, periodo or hoy_local())


@router.get("/no-debt-certificate/{property_id}", dependencies=tesorero_only)
async def no_debt_certificate(
    property_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Reglamento Art. 16: constancia de no adeudo para la venta de una vivienda.
    Solo se emite si no hay ningún cargo sin pagar (aunque aún esté dentro de
    plazo: la constancia dice "al corriente", y un cargo pendiente ya es deuda).
    """
    estado = await get_account_statement(db, property_id)
    if estado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    if estado.deuda_total > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "La vivienda tiene adeudos: no se puede emitir la constancia")

    propiedad: Property = estado.propiedad
    tenant = await db.get(Tenant, uuid.UUID(current_user.tenant_id))
    pdf_bytes = build_no_debt_certificate_pdf(propiedad, tenant, hoy_local())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="constancia-no-adeudo-{propiedad.id}.pdf"'},
    )
