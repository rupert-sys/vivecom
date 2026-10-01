import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import ControlBase


class Tenant(ControlBase):
    """Vive en el schema público de control. Ver modelo_datos_vivecom.md."""

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String)
    # unique=True: la CLABE es el ÚNICO mecanismo para enrutar un depósito
    # SPEI entrante al tenant correcto (ver deposit_processing_service.py) —
    # dos tenants con la misma CLABE hacen que ese enrutamiento truene con
    # MultipleResultsFound. Bug real encontrado en F1-29 al construir la
    # prueba de punta a punta del flujo de cobro. La restricción se valida
    # también a mano en /signup y en PATCH /tenant/clabe antes de escribir,
    # porque agregar el índice único aquí no lo aplica retroactivamente a
    # una base ya existente con duplicados (mismo límite que
    # migrate_add_tables.py: solo crea tablas, no altera columnas ni
    # restricciones de tablas ya existentes).
    # nullable=True: /signup (landing de bienvenida) ya no la pide — un condominio
    # nuevo no puede recibir SPEI hasta que el admin la configure desde /clabe
    # (PATCH /tenant/clabe, que ya maneja clabe_anterior=None como "se está
    # configurando por primera vez", no como un cambio real).
    clabe_destino: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    precio_por_vivienda: Mapped[float] = mapped_column(Numeric(10, 2), default=25.00)
    schema_name: Mapped[str] = mapped_column(String, unique=True)
    # Logo del condominio (opcional): los bytes viven en el almacenamiento (file_storage.py, misma llave
    # fija por tenant, así que un re-subido pisa al anterior en vez de acumular huérfanos); aquí solo se
    # guarda el tipo, para saber si hay logo y con qué Content-Type servirlo (ver GET /tenant/logo).
    logo_content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # Portal de administrador principal (staff Vivecom, ver api/staff_tenants.py): desactivar un condominio
    # bloquea el login de todo ese tenant (ver la revisión en api/auth.py) — es lo único que le da efecto real
    # a "suspender" un condominio desde el portal, en vez de ser solo una bandera cosmética.
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # default (no server_default): igual que created_at en el resto de los modelos (ver announcement.py,
    # incident.py, etc.), se fija en Python al construir el objeto, no en la base — así se comporta igual en
    # SQLite (pruebas) y en Postgres real. Los ~200 tenants ya existentes en producción no tienen este valor
    # calculado por la app: se hace un ALTER TABLE con DEFAULT now() una sola vez para ellos (ver
    # init_db.init_control_schema), que es un mecanismo aparte de este default de Python.
    # .replace(tzinfo=None): la columna es TIMESTAMP WITHOUT TIME ZONE (mismo patrón que el resto del
    # proyecto, ver incidents.py/announcement_service.py/etc.) — asyncpg rechaza un datetime CON tzinfo
    # contra esa columna ("can't subtract offset-naive and offset-aware datetimes"). Bug real: encontrado
    # creando el primer tenant nuevo contra Postgres real (SQLite no distingue tz-aware de tz-naive, así
    # que las pruebas nunca lo detectaron).
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    # Papelera del portal de administrador principal (ver api/staff_tenants.py): un condominio enviado a la
    # papelera también se desactiva (activo=False, mismo bloqueo de login) — la papelera es un paso PREVIO y
    # reversible a borrarlo (DELETE /staff/tenants/{id}), nunca el borrado mismo. Solo se puede borrar en
    # definitiva un tenant que ya esté aquí, y esa acción sí es irreversible (DROP SCHEMA).
    en_papelera: Mapped[bool] = mapped_column(Boolean, default=False)
    papelera_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
