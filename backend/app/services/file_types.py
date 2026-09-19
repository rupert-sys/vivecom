"""
Qué archivos se aceptan como comprobante y cómo se reconocen. El tipo se decide
por los BYTES del archivo, nunca por la extensión ni por el Content-Type que
declare el cliente: quien sube algo puede mentir en ambos. Solo fotos y PDF —
sin SVG ni HTML, que un navegador ejecutaría al abrirlos desde nuestro dominio.
"""

_BRANDS_HEIC = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}

MENSAJE_TIPO_NO_ACEPTADO = "Solo se aceptan fotos (JPG, PNG, WEBP, HEIC) o PDF."


def detectar_tipo(datos: bytes) -> str | None:
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if datos.startswith(b"%PDF-"):
        return "application/pdf"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    # Fotos del iPhone: contenedor ISO-BMFF con la marca "heic"/"mif1"... en el byte 8.
    if datos[4:8] == b"ftyp" and datos[8:12] in _BRANDS_HEIC:
        return "image/heic"
    return None
