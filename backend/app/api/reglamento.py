"""
Reglas del reglamento interior del condominio que cambian cómo se comporta el
sistema (recargo por mora, pago en efectivo, restricciones a morosos, umbral de
gastos, cajones de visitas). Ver models/reglamento.py.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.reglamento import ReglamentoConfig
from app.models.user import Rol
from app.schemas.reglamento import ReglamentoRead, ReglamentoUpdate
from app.services.reglamento_service import Reglamento, get_reglamento, reglamento_de_fila

router = APIRouter(prefix="/tenant/reglamento", tags=["tenant-config"])

admin_only = [Depends(require_roles(Rol.admin))]


def _a_lectura(reglamento: Reglamento) -> ReglamentoRead:
    return ReglamentoRead(**asdict(reglamento), dia_recargo=reglamento.dia_recargo)


@router.get("", response_model=ReglamentoRead)
async def leer_reglamento(db: AsyncSession = Depends(get_tenant_db)):
    """Cualquier rol autenticado: las reglas del condominio no son secretas, y las apps las muestran."""
    return _a_lectura(await get_reglamento(db))


@router.patch("", response_model=ReglamentoRead, dependencies=admin_only)
async def actualizar_reglamento(payload: ReglamentoUpdate, db: AsyncSession = Depends(get_tenant_db)):
    fila = (await db.execute(select(ReglamentoConfig).where(ReglamentoConfig.id == 1))).scalar_one_or_none()
    actual = asdict(reglamento_de_fila(fila))
    # exclude_unset: solo se cambia lo que el cliente mandó — incluido un
    # gasto_umbral_asamblea explícito en null para quitar el umbral.
    actual.update(payload.model_dump(exclude_unset=True))

    if fila is None:
        fila = ReglamentoConfig(id=1)
        db.add(fila)
    for campo, valor in actual.items():
        setattr(fila, campo, valor)
    await db.commit()
    return _a_lectura(reglamento_de_fila(fila))
