import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.amenity import Amenity, AmenityApprover
from app.models.reservation import EstadoReserva, Reservation
from app.models.user import Rol, UserAccount
from app.schemas.amenity import AmenityApproverCreate, AmenityBusySlot, AmenityCreate, AmenityRead

router = APIRouter(prefix="/amenities", tags=["amenities"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("", response_model=AmenityRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_amenity(payload: AmenityCreate, db: AsyncSession = Depends(get_tenant_db)):
    amenidad = Amenity(nombre=payload.nombre, periodo_limite_horas=payload.periodo_limite_horas)
    db.add(amenidad)
    await db.commit()
    return amenidad


@router.get("", response_model=list[AmenityRead])
async def list_amenities(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Amenity).order_by(Amenity.nombre))
    return result.scalars().all()


@router.get("/{amenity_id}/availability", response_model=list[AmenityBusySlot])
async def amenity_availability(amenity_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    """
    HU-C06: horarios ya ocupados (pendientes o aprobados) de esta amenidad,
    para que el residente elija un horario libre antes de solicitar. Sin
    property_id: cualquier residente puede consultarlo, pero no necesita
    saber de quién es cada reservación ajena.
    """
    result = await db.execute(
        select(Reservation.fecha_inicio, Reservation.fecha_fin).where(
            Reservation.amenity_id == amenity_id,
            Reservation.estado.in_([EstadoReserva.pendiente, EstadoReserva.aprobada]),
        )
    )
    return [AmenityBusySlot(fecha_inicio=inicio, fecha_fin=fin) for inicio, fin in result.all()]


@router.post(
    "/{amenity_id}/approvers", status_code=status.HTTP_201_CREATED, dependencies=admin_only,
)
async def add_amenity_approver(amenity_id: uuid.UUID, payload: AmenityApproverCreate, db: AsyncSession = Depends(get_tenant_db)):
    """HU-C07: el administrador designa quién aprueba reservaciones de esta amenidad."""
    amenidad = await db.get(Amenity, amenity_id)
    if amenidad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Amenidad no encontrada")

    usuario = await db.get(UserAccount, payload.user_id)
    if usuario is None or usuario.rol != Rol.comite_aprobador:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El usuario debe existir y tener el rol comite_aprobador")

    existente = (
        await db.execute(
            select(AmenityApprover).where(
                AmenityApprover.amenity_id == amenity_id, AmenityApprover.user_id == payload.user_id
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este usuario ya es aprobador de esta amenidad")

    db.add(AmenityApprover(amenity_id=amenity_id, user_id=payload.user_id))
    await db.commit()
    return {"amenity_id": str(amenity_id), "user_id": str(payload.user_id)}


@router.get("/{amenity_id}/approvers", response_model=list[uuid.UUID], dependencies=admin_only)
async def list_amenity_approvers(amenity_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(AmenityApprover.user_id).where(AmenityApprover.amenity_id == amenity_id))
    return result.scalars().all()
