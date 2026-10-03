"""
Script de una sola vez (F0-12): crea las cuentas de tesorería, vigilancia y vocero
que faltan en los tenants que ya existían ANTES de que provision_tenant_con_casas
empezara a generarlas (ver provisioning.py) — hasta entonces, un condominio solo
tenía admin + residentes, y tesorería/vigilancia/vocero quedaban sin ninguna
cuenta utilizable hasta que alguien los daba de alta a mano desde Usuarios.

Idempotente: si un tenant ya tiene cuenta de un rol (dada de alta a mano o por
una corrida anterior de este script), no la toca. Puede correrse las veces que
haga falta.

Uso: python -m app.core.backfill_personal_accounts
"""

import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal, tenant_session
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import Rol, UserAccount
from app.models.user_lookup import UserLookup

# Mismos prefijos de email que usa provision_tenant_con_casas para un tenant nuevo.
PREFIJOS_EMAIL: dict[Rol, str] = {Rol.tesorero: "tesoreria", Rol.guardia: "vigilancia", Rol.vocero: "vocero"}


async def backfill_un_tenant(tenant: Tenant) -> list[str]:
    creadas: list[str] = []
    async with tenant_session(tenant.schema_name) as db:
        admin = (await db.execute(select(UserAccount).where(UserAccount.rol == Rol.admin))).scalars().first()
        if admin is None:
            print(f"{tenant.nombre} ({tenant.schema_name}): sin cuenta de admin, se omite — revisar a mano.")
            return creadas
        dominio = admin.email.split("@", 1)[1]

        roles_existentes = {fila[0] for fila in (await db.execute(select(UserAccount.rol))).all()}
        for rol, prefijo in PREFIJOS_EMAIL.items():
            if rol in roles_existentes:
                continue
            email = f"{prefijo}@{dominio}"
            cuenta = UserAccount(
                email=email, password_hash=hash_password(tenant.nombre), rol=rol, debe_cambiar_password=True,
            )
            db.add(cuenta)
            await db.flush()  # necesitamos cuenta.id antes de escribir el lookup (mismo motivo que provisioning.py)
            db.add(UserLookup(email=email, tenant_id=tenant.id, user_id=cuenta.id))
            creadas.append(email)
        await db.commit()
    return creadas


async def main() -> None:
    async with SessionLocal() as db:
        tenants = (await db.execute(select(Tenant).where(Tenant.en_papelera.is_(False)))).scalars().all()

    for tenant in tenants:
        creadas = await backfill_un_tenant(tenant)
        if creadas:
            print(f"{tenant.nombre} ({tenant.schema_name}): creadas {', '.join(creadas)} — contraseña inicial: el nombre del condominio.")
        else:
            print(f"{tenant.nombre} ({tenant.schema_name}): ya tenía las 3 cuentas, sin cambios.")


if __name__ == "__main__":
    asyncio.run(main())
