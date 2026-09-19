import uuid

from pydantic import BaseModel


class FileRead(BaseModel):
    id: uuid.UUID
    nombre_original: str
    content_type: str
    size: int
    # Referencia interna (/files/<id>) que se guarda en comprobante_url.
    ref: str


class FileLink(BaseModel):
    url: str
    expira_en_segundos: int
