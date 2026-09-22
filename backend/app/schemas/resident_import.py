from pydantic import BaseModel


class ResidentImportError(BaseModel):
    fila: int  # número de fila del Excel (1 = encabezado), para que el administrador la ubique fácil
    motivo: str


class ResidentImportResult(BaseModel):
    total_filas: int
    viviendas_creadas: int
    residentes_creados: int
    residentes_actualizados: int  # ya existía un residente con ese correo; se actualizaron nombre/teléfono
    vinculos_creados: int  # residente ligado a una vivienda (propietario/inquilino)
    vinculos_actualizados: int  # ya estaba ligado; solo cambió si era propietario o inquilino
    filas_con_error: list[ResidentImportError]
