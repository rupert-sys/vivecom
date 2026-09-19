"""
Enlaces firmados a archivos. El comprobante de un gasto o de un pago se abre con
un simple enlace (un <a> del navegador, url_launcher en la app) que no puede
llevar el encabezado Authorization, así que la propia URL trae una firma de vida
corta. La firma usa una llave DISTINTA a la de los tokens de sesión: un enlace de
archivo no sirve como token de acceso, ni al revés.
"""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import jwt

from app.core.config import settings

PREFIJO_INTERNO = "/files/"


def _llave() -> str:
    return f"{settings.jwt_secret}|file-link"


def firmar_url(file_id: uuid.UUID, schema_name: str) -> str:
    ahora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "fid": str(file_id), "schema": schema_name, "typ": "file-link",
            "iat": ahora, "exp": ahora + timedelta(seconds=settings.file_link_ttl_seconds),
        },
        _llave(),
        algorithm="HS256",
    )
    return f"{settings.public_base_url.rstrip('/')}{PREFIJO_INTERNO}{file_id}/content?t={quote(token)}"


def verificar_enlace(token: str) -> tuple[uuid.UUID, str]:
    """(file_id, schema). Lanza jwt.InvalidTokenError si la firma no es válida o ya venció."""
    datos = jwt.decode(token, _llave(), algorithms=["HS256"])
    if datos.get("typ") != "file-link":
        raise jwt.InvalidTokenError("no es un enlace de archivo")
    return uuid.UUID(datos["fid"]), datos["schema"]


def referencia_interna(file_id: uuid.UUID) -> str:
    """Lo que se guarda en comprobante_url cuando el comprobante es un archivo subido."""
    return f"{PREFIJO_INTERNO}{file_id}"


def resolver_url(valor: str | None, schema_name: str) -> str | None:
    """Convierte una referencia interna (/files/<id>) en un enlace firmado; una URL externa queda igual."""
    if valor and valor.startswith(PREFIJO_INTERNO):
        try:
            return firmar_url(uuid.UUID(valor[len(PREFIJO_INTERNO):]), schema_name)
        except ValueError:
            return valor
    return valor
