"""
F3-04: crea (o actualiza la contraseña de) una cuenta de VivecomStaff. No
hay endpoint público para esto a propósito (ver la nota de alcance en
app/models/vivecom_staff.py) — un empleado de Vivecom con acceso al
dashboard ejecutivo agregado ve datos financieros de TODOS los
condominios, así que solo un operador con acceso directo al servidor
puede crear una cuenta de este tipo.

Uso:
    python -m app.core.crear_staff --email ruperto@vivecom.mx --password "una-contraseña-fuerte"
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.vivecom_staff import VivecomStaff


async def crear_o_actualizar(email: str, password: str) -> None:
    async with SessionLocal() as db:
        existente = (await db.execute(select(VivecomStaff).where(VivecomStaff.email == email))).scalar_one_or_none()
        if existente is not None:
            existente.password_hash = hash_password(password)
            await db.commit()
            print(f"Contraseña actualizada para {email}.")
            return

        db.add(VivecomStaff(email=email, password_hash=hash_password(password)))
        await db.commit()
        print(f"Cuenta de staff creada: {email}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    asyncio.run(crear_o_actualizar(args.email, args.password))
