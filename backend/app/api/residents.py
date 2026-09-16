import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_db, require_roles
from app.models.property import Property
from app.models.resident import Resident, ResidentProperty
from app.models.user import Rol
from app.schemas.resident import LinkResidentToProperty, ResidentCreate, ResidentRead, ResidentUpdate

router = APIRouter(tags=["residents"])

admin_only = [Depends(require_roles(Rol.admin))]


@router.post("/residents", response_model=ResidentRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_resident(payload: ResidentCreate, db: AsyncSession = Depends(get_tenant_db)):
    resident = Resident(nombre=payload.nombre, telefono=payload.telefono, email=payload.email)
    db.add(resident)
    await db.commit()
    # Sin refresh() por la misma razón que en properties.py: el search_path
    # transaccional del tenant ya no aplica después del commit.
    return resident


@router.get("/residents", response_model=list[ResidentRead])
async def list_residents(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Resident).order_by(Resident.nombre))
    return result.scalars().all()


@router.get("/residents/{resident_id}", response_model=ResidentRead)
async def get_resident(resident_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    resident = await db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Residente no encontrado")
    return resident


@router.patch("/residents/{resident_id}", response_model=ResidentRead, dependencies=admin_only)
async def update_resident(resident_id: uuid.UUID, payload: ResidentUpdate, db: AsyncSession = Depends(get_tenant_db)):
    resident = await db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Residente no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resident, field, value)
    await db.commit()
    return resident


# ---------- Relación N:N con Property ----------
# Ver alcance sección 2: un residente puede tener varias viviendas, cada una
# se administra de forma independiente. Estos endpoints solo gestionan el vínculo.

@router.post(
    "/properties/{property_id}/residents",
    status_code=status.HTTP_201_CREATED,
    dependencies=admin_only,
)
async def link_resident_to_property(
    property_id: uuid.UUID, payload: LinkResidentToProperty, db: AsyncSession = Depends(get_tenant_db)
):
    prop = await db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vivienda no encontrada")
    resident = await db.get(Resident, payload.resident_id)
    if resident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Residente no encontrado")

    existing = (
        await db.execute(
            select(ResidentProperty).where(
                ResidentProperty.resident_id == resident.id,
                ResidentProperty.property_id == prop.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este residente ya está ligado a esta vivienda")

    link = ResidentProperty(resident_id=resident.id, property_id=prop.id, rol=payload.rol)
    db.add(link)
    await db.commit()
    return {"resident_id": str(resident.id), "property_id": str(prop.id), "rol": payload.rol.value}


@router.get("/properties/{property_id}/residents", response_model=list[ResidentRead])
async def list_property_residents(property_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(Resident).join(ResidentProperty).where(ResidentProperty.property_id == property_id)
    )
    return result.scalars().all()


@router.delete(
    "/properties/{property_id}/residents/{resident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin_only,
)
async def unlink_resident_from_property(
    property_id: uuid.UUID, resident_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)
):
    link = (
        await db.execute(
            select(ResidentProperty).where(
                ResidentProperty.resident_id == resident_id,
                ResidentProperty.property_id == property_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese residente no está ligado a esta vivienda")
    await db.delete(link)
    await db.commit()
