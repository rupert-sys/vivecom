from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import control_session
from app.core.provisioning import provision_tenant_con_casas
from app.schemas.signup import TenantSignupRequest, TenantSignupResponse
from app.services.tenant_domain import generar_dominio_unico

router = APIRouter(prefix="/signup", tags=["signup"])


@router.post("", response_model=TenantSignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: TenantSignupRequest, control_db: AsyncSession = Depends(control_session)):
    """
    Landing de bienvenida del panel: da de alta un condominio sin intervención manual del equipo (F3-06), en
    dos pasos — datos del condominio (nombre, cantidad de viviendas) y datos de quien se registra (nombre,
    teléfono). No pide CLABE ni que el admin invente su propio email/contraseña:

    - El email del admin es administracion@<dominio>, donde <dominio> sale del nombre del condominio (ver
      tenant_domain.slug_de_condominio) — nunca es un dominio real que reciba correo (el proyecto no tiene
      canal de correo, solo WhatsApp+SMS: el email aquí es únicamente un identificador único de login).
    - Su contraseña inicial es el propio nombre del condominio, con debe_cambiar_password=True para que la
      cambie de inmediato al entrar (ver create_access_token).
    - Se crean de una vez las `cantidad_casas` viviendas ("Casa 1".."Casa N") y, por cada una, una cuenta de
      residente SIN ACTIVAR en casa<n>@<dominio> — el residente la reclama desde la app con sus propios datos
      (nombre, si es dueño o renta, teléfono y contraseña): POST /residents/activar.
    - También se crea de una vez una cuenta utilizable de tesorería, vigilancia y vocero (misma contraseña
      inicial que el admin) — ver provision_tenant_con_casas.
    - La CLABE se configura después, desde /clabe (PATCH /tenant/clabe) — el condominio no puede recibir SPEI
      hasta entonces, pero eso no bloquea nada del resto del panel.

    AVISO DE SEGURIDAD (igual que la versión anterior de este endpoint, ver bitácora F3-06): es PÚBLICO, sin
    autenticación, sin rate-limiting ni CAPTCHA, y crea un schema de Postgres completo (más hasta
    MAX_CASAS_POR_SIGNUP cuentas) por cada llamada exitosa. Válido para probar el flujo y para demos; antes de
    exponerlo en producción real hace falta agregar al menos una de esas protecciones.
    """
    dominio = await generar_dominio_unico(control_db, payload.nombre_condominio)

    tenant, emails_viviendas, emails_personal = await provision_tenant_con_casas(
        payload.nombre_condominio, payload.cantidad_casas, dominio, payload.nombre_admin, payload.telefono_admin,
    )

    return TenantSignupResponse(
        tenant_id=tenant.id, nombre=tenant.nombre, admin_email=f"administracion@{dominio}",
        emails_viviendas=emails_viviendas, email_tesorero=emails_personal["tesorero"],
        email_guardia=emails_personal["guardia"], email_vocero=emails_personal["vocero"],
    )
