"""
Subida y descarga de archivos (comprobantes de gastos y de pagos). Las fotos y PDF se
validan por sus bytes, se guardan con una llave generada por el servidor y se sirven
solo con un enlace firmado de vida corta — el bucket/disco nunca se expone directo.
"""

import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, enlace_de_archivo, get_current_user, get_link_tenant_db, get_tenant_db
from app.core.config import settings
from app.models.stored_file import StoredFile
from app.models.user import Rol
from app.schemas.file import FileLink, FileRead
from app.services.file_links import firmar_url, referencia_interna
from app.services.file_storage import get_storage
from app.services.file_types import MENSAJE_TIPO_NO_ACEPTADO, detectar_tipo

router = APIRouter(prefix="/files", tags=["files"])

STAFF_FINANZAS = {Rol.admin.value, Rol.tesorero.value}

# Quién puede SUBIR cada clase de archivo.
_SUBEN = {
    "gasto": {Rol.admin.value},  # solo el administrador registra gastos (POST /expenses)
    "pago": None,  # cualquier usuario autenticado (el residente adjunta su comprobante del banco)
    "incidencia": {Rol.admin.value, Rol.guardia.value, Rol.comite_aprobador.value},
    "acuerdo": None,  # el escrito o documento de respaldo de una solicitud de acuerdo de pago (cualquier residente)
}


def puede_ver(archivo: StoredFile, usuario: CurrentUser) -> bool:
    """
    Quien lo subió siempre puede verlo. Además: los comprobantes de gastos son de transparencia
    (HU-A12: cualquier residente los consulta); los de pagos, solo tesorería; los de incidencias,
    quienes las gestionan.
    """
    if str(archivo.uploaded_by) == usuario.user_id:
        return True
    if archivo.kind == "gasto":
        return True
    if archivo.kind == "pago":
        return usuario.rol in STAFF_FINANZAS
    if archivo.kind == "acuerdo":  # lo ve quien decide o da seguimiento al acuerdo
        return usuario.rol in {Rol.comite_lectura.value, Rol.comite_aprobador.value} | STAFF_FINANZAS
    if archivo.kind == "incidencia":
        return usuario.rol in {Rol.admin.value, Rol.guardia.value, Rol.comite_lectura.value, Rol.comite_aprobador.value}
    return False


def _nombre_seguro(nombre: str | None) -> str:
    # Solo el nombre, sin rutas ni caracteres de control (se usa en Content-Disposition).
    limpio = re.sub(r"[\x00-\x1f\x7f\\/]", "_", (nombre or "archivo").split("/")[-1].split("\\")[-1]).strip()
    return (limpio or "archivo")[:120]


@router.post("", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    kind: str = Form("pago"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Sube una foto (JPG, PNG, WEBP, HEIC) o un PDF de hasta 10 MB. Regresa su `id` y su `ref`
    para adjuntarlo a un gasto (`comprobante_archivo_id`) o a un comprobante de pago.
    """
    if kind not in _SUBEN:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "kind debe ser gasto, pago, incidencia o acuerdo")
    permitidos = _SUBEN[kind]
    if permitidos is not None and current_user.rol not in permitidos:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para subir este tipo de archivo")

    # Se lee un byte de más para distinguir "exactamente el límite" de "se pasó" sin cargar todo en memoria.
    datos = await file.read(settings.max_upload_bytes + 1)
    if len(datos) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"El archivo pesa más de {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )
    if not datos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo está vacío.")
    tipo = detectar_tipo(datos)
    if tipo is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, MENSAJE_TIPO_NO_ACEPTADO)

    file_id = uuid.uuid4()
    # La llave la decide el servidor (schema/uuid): el nombre que mande el cliente no toca el disco.
    key = f"{current_user.schema_name}/{file_id}"
    await get_storage().save(key, datos, tipo)
    archivo = StoredFile(
        id=file_id, uploaded_by=uuid.UUID(current_user.user_id), kind=kind,
        nombre_original=_nombre_seguro(file.filename), content_type=tipo, size=len(datos),
        storage_key=key, created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(archivo)
    await db.commit()
    return FileRead(
        id=archivo.id, nombre_original=archivo.nombre_original, content_type=tipo, size=archivo.size,
        ref=referencia_interna(archivo.id),
    )


@router.get("/{file_id}/link", response_model=FileLink)
async def get_file_link(
    file_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Un enlace firmado de vida corta para abrir el archivo (si el usuario tiene derecho a verlo)."""
    archivo = await db.get(StoredFile, file_id)
    # 404 (no 403) cuando no puede verlo: no se confirma que un archivo ajeno exista.
    if archivo is None or not puede_ver(archivo, current_user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    return FileLink(url=firmar_url(archivo.id, current_user.schema_name), expira_en_segundos=settings.file_link_ttl_seconds)


@router.get("/{file_id}/content")
async def download_file(
    file_id: uuid.UUID,
    enlace: tuple[uuid.UUID, str] = Depends(enlace_de_archivo),
    db: AsyncSession = Depends(get_link_tenant_db),
):
    """El contenido, con el enlace firmado como única credencial (lo abre un navegador o url_launcher)."""
    if enlace[0] != file_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Enlace inválido")
    archivo = await db.get(StoredFile, file_id)
    if archivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    datos = await get_storage().read(archivo.storage_key)
    return Response(
        content=datos,
        media_type=archivo.content_type,  # el detectado por los bytes, nunca el que declaró el cliente
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(archivo.nombre_original)}",
            "X-Content-Type-Options": "nosniff",  # que el navegador no reinterprete el tipo
            "Cache-Control": "private, max-age=300",
        },
    )
