"""
Dónde viven los bytes de los archivos subidos. Dos implementaciones con la misma
interfaz: disco local (desarrollo) y S3 (producción). La base solo guarda la
`storage_key`; cambiar de una a otra no toca la base de datos.
"""

import asyncio
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class FileStorage(Protocol):
    async def save(self, key: str, data: bytes, content_type: str) -> None: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalFileStorage:
    """Disco local. Solo para desarrollo: en un contenedor el disco es efímero."""

    def __init__(self, root: str | Path):
        self._root = Path(root).resolve()

    def _ruta(self, key: str) -> Path:
        ruta = (self._root / key).resolve()
        # La key la genera el servidor (schema/uuid), pero se comprueba igual: nunca salir de la raíz.
        if self._root not in ruta.parents:
            raise ValueError("storage_key fuera del directorio de almacenamiento")
        return ruta

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        ruta = self._ruta(key)

        def escribir():
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(data)

        await asyncio.to_thread(escribir)

    async def read(self, key: str) -> bytes:
        return await asyncio.to_thread(self._ruta(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._ruta(key).unlink, True)


class S3FileStorage:
    """
    S3 (o compatible). Las llamadas de boto3 son bloqueantes, así que corren en un
    hilo. El bucket debe ser PRIVADO: los archivos solo se sirven a través de la
    API con un enlace firmado por Vivecom, nunca por una URL pública del bucket.
    """

    def __init__(self, bucket: str, client=None, region: str = "us-east-1"):
        self._bucket = bucket
        if client is None:
            import boto3  # import diferido: solo hace falta con STORAGE_BACKEND=s3

            client = boto3.client("s3", region_name=region)
        self._client = client

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256",
        )

    async def read(self, key: str) -> bytes:
        respuesta = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        return await asyncio.to_thread(respuesta["Body"].read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)


_storage: FileStorage | None = None


def get_storage() -> FileStorage:
    global _storage
    if _storage is None:
        if settings.storage_backend == "s3":
            if not settings.storage_s3_bucket:
                raise RuntimeError("STORAGE_BACKEND=s3 requiere STORAGE_S3_BUCKET")
            _storage = S3FileStorage(settings.storage_s3_bucket, region=settings.storage_s3_region)
        else:
            if settings.environment == "production":
                # Fail-closed, mismo criterio que el secreto del webhook SPEI (F2-21): en un
                # contenedor el disco se borra al redesplegar y se perderían los comprobantes.
                raise RuntimeError("En producción los archivos deben ir a S3 (STORAGE_BACKEND=s3), no a disco local")
            _storage = LocalFileStorage(settings.storage_local_dir)
    return _storage


def set_storage(storage: FileStorage | None) -> None:
    """Para las pruebas: reemplaza (o restablece con None) el almacenamiento."""
    global _storage
    _storage = storage
