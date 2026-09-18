"""F3-04: dashboard ejecutivo agregado — ver la nota de alcance en app/models/vivecom_staff.py."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_staff
from app.core.database import control_session
from app.schemas.staff import CurrentStaff, ExecutiveSummary
from app.services.executive_report_service import get_executive_summary

router = APIRouter(prefix="/staff/reportes", tags=["staff"])


@router.get("/resumen-ejecutivo", response_model=ExecutiveSummary)
async def resumen_ejecutivo(
    hoy: date | None = None,
    current_staff: CurrentStaff = Depends(get_current_staff),
    control_db: AsyncSession = Depends(control_session),
):
    """
    Agrega, sobre TODOS los tenants: viviendas, ingresos confirmados del mes
    (de `hoy`, o el mes actual si no se manda), deuda pendiente/vencida, y
    tasa de morosidad. `hoy` es un parámetro de query solo para poder
    probarlo de forma determinística — el uso real siempre lo deja vacío.
    """
    return await get_executive_summary(control_db, hoy)
