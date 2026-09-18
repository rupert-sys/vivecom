"""
F3-04: dashboard ejecutivo agregado para el equipo interno de Vivecom (no
para clientes) — ver la nota de alcance en app/models/vivecom_staff.py sobre
por qué "administradora que administra varios condominios" se interpretó
así en vez de como un nuevo tipo de cuenta cliente cross-tenant.

Mismo patrón de recorrer todos los tenants que ya usa app/workers/tasks.py:
un tenant con error no debe tumbar el reporte completo de los demás — se
excluye de los totales y de la lista, no se propaga la excepción.
"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import tenant_session
from app.models.fee_charge import EstadoCargo, FeeCharge
from app.models.incident import EstadoIncidencia, Incident
from app.models.payment import EstadoPago, Payment
from app.models.property import Property
from app.models.tenant import Tenant
from app.schemas.staff import ExecutiveSummary, ExecutiveTenantSummary, ExecutiveTotales

logger = logging.getLogger(__name__)


async def _resumen_de_un_tenant(schema_name: str, inicio_mes: date) -> dict:
    async with tenant_session(schema_name) as db:
        viviendas = (await db.execute(select(func.count(Property.id)))).scalar() or 0

        ingresos = (
            await db.execute(
                select(func.coalesce(func.sum(Payment.monto), 0)).where(
                    Payment.estado == EstadoPago.confirmado, Payment.fecha_deteccion >= inicio_mes
                )
            )
        ).scalar()

        deuda = (
            await db.execute(
                select(func.coalesce(func.sum(FeeCharge.monto_base + FeeCharge.recargo_aplicado), 0)).where(
                    FeeCharge.estado.in_([EstadoCargo.pendiente, EstadoCargo.vencido])
                )
            )
        ).scalar()

        cargos_totales = (await db.execute(select(func.count(FeeCharge.id)))).scalar() or 0
        cargos_vencidos = (
            await db.execute(select(func.count(FeeCharge.id)).where(FeeCharge.estado == EstadoCargo.vencido))
        ).scalar() or 0

        incidencias_abiertas = (
            await db.execute(
                select(func.count(Incident.id)).where(Incident.estado != EstadoIncidencia.resuelta)
            )
        ).scalar() or 0

        return {
            "viviendas": viviendas,
            "ingresos_mes_actual": float(ingresos),
            "deuda_pendiente": float(deuda),
            "cargos_totales": cargos_totales,
            "cargos_vencidos": cargos_vencidos,
            "incidencias_abiertas": incidencias_abiertas,
        }


async def get_executive_summary(control_db: AsyncSession, hoy: date | None = None) -> ExecutiveSummary:
    hoy = hoy or datetime.now(timezone.utc).date()
    inicio_mes = hoy.replace(day=1)

    tenants = (await control_db.execute(select(Tenant))).scalars().all()

    resumenes: list[ExecutiveTenantSummary] = []
    for tenant in tenants:
        try:
            datos = await _resumen_de_un_tenant(tenant.schema_name, inicio_mes)
        except Exception:  # noqa: BLE001 — un tenant con error no debe tumbar el reporte de los demás
            logger.exception("No se pudo generar el resumen ejecutivo del tenant %s", tenant.schema_name)
            continue
        resumenes.append(ExecutiveTenantSummary(tenant_id=tenant.id, nombre=tenant.nombre, **datos))

    cargos_totales = sum(r.cargos_totales for r in resumenes)
    cargos_vencidos = sum(r.cargos_vencidos for r in resumenes)

    totales = ExecutiveTotales(
        total_condominios=len(resumenes),
        total_viviendas=sum(r.viviendas for r in resumenes),
        ingresos_mes_actual=sum(r.ingresos_mes_actual for r in resumenes),
        deuda_pendiente=sum(r.deuda_pendiente for r in resumenes),
        tasa_morosidad=(cargos_vencidos / cargos_totales) if cargos_totales else 0.0,
        incidencias_abiertas=sum(r.incidencias_abiertas for r in resumenes),
    )

    return ExecutiveSummary(periodo=inicio_mes.strftime("%Y-%m"), tenants=resumenes, totales=totales)
