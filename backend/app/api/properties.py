import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_roles
from app.models.property import Property
from app.models.user import Rol
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate
from app.schemas.statement import AccountStatement
from app.services.payment_reference import generate_payment_reference
from app.services.reglamento_service import acuerdos_vigentes, get_reglamento, hoy_local, vivienda_en_mora
from app.services.statement_service import get_account_statement

router = APIRouter(prefix="/properties", tags=["properties"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_property(payload: PropertyCreate, db: AsyncSession = Depends(get_tenant_db)):
    referencia = await generate_payment_reference(payload.identificador, db)
    prop = Property(identificador=payload.identificador, referencia_pago=referencia)
    db.add(prop)
    await db.commit()
    # No hace falta refresh(): el id se genera en Python (uuid.uuid4) antes del
    # insert, así que `prop` ya tiene todos sus campos actualizados en memoria.
    # Un refresh() aquí fallaría: el search_path del tenant es transaccional y
    # ya no aplica después del commit (ver core/database.py).
    return prop


@router.get("", response_model=list[PropertyRead])
async def list_properties(db: AsyncSession = Depends(get_tenant_db)):
    # Lectura abierta a cualquier rol autenticado del tenant (admin, tesorero, guardia, etc.)
    result = await db.execute(select(Property).order_by(Property.identificador))
    return result.scalars().all()


@router.get("/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    # F2-21: mismo control de acceso que get_property_statement — a
    # diferencia de list_properties (abierto a todo el tenant a propósito,
    # transparencia financiera del condominio en su conjunto), este endpoint
    # expone referencia_pago/saldo_a_favor de UNA vivienda puntual, y un
    # residente no debe poder leer los de otra vivienda solo adivinando el id.
    es_staff = current_user.rol in {Rol.admin.value, Rol.tesorero.value}
    if not es_staff and current_user.property_id != str(property_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta vivienda")

    prop = await db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    return prop


@router.get("/{property_id}/statement", response_model=AccountStatement)
async def get_property_statement(
    property_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    F1-14: historial de cargos y pagos, más el saldo actual (a favor o en
    contra). Mismo control de acceso que el recibo de F1-11: admin/tesorero
    ven cualquiera, un residente solo el de su propia vivienda.
    """
    es_staff = current_user.rol in {Rol.admin.value, Rol.tesorero.value}
    if not es_staff and current_user.property_id != str(property_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a este estado de cuenta")

    estado = await get_account_statement(db, property_id)
    if estado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")

    reglamento = await get_reglamento(db)
    en_mora = await vivienda_en_mora(db, property_id, hoy_local(), reglamento)
    restricciones = []
    if en_mora and reglamento.morosos_sin_voto:
        restricciones.append("No puedes votar en las votaciones (conservas voz, pero no voto).")
    if en_mora and reglamento.morosos_sin_areas_comunes:
        restricciones.append("No puedes reservar áreas comunes.")

    return AccountStatement(
        en_mora=en_mora,
        en_acuerdo=bool(await acuerdos_vigentes(db, property_id)),
        restricciones_por_mora=restricciones,
        property_id=estado.propiedad.id,
        identificador=estado.propiedad.identificador,
        saldo_a_favor=float(estado.propiedad.saldo_a_favor),
        deuda_total=estado.deuda_total,
        cargos=estado.cargos,
        pagos=estado.pagos,
    )


@router.patch("/{property_id}", response_model=PropertyRead, dependencies=admin_only)
async def update_property(property_id: uuid.UUID, payload: PropertyUpdate, db: AsyncSession = Depends(get_tenant_db)):
    prop = await db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    if payload.identificador is not None:
        prop.identificador = payload.identificador
    await db.commit()
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
async def delete_property(property_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    prop = await db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    await db.delete(prop)
    await db.commit()
