"""
Subida y descarga de archivos (comprobantes de gastos y de pagos): validación por los bytes,
permisos por tipo de archivo y enlaces firmados de vida corta.
"""

import uuid
from types import SimpleNamespace
from urllib.parse import urlsplit

import jwt
import pytest

from app.api.deps import get_current_user
from app.core.config import settings
from app.main import app
from app.schemas.auth import CurrentUser
from app.services import file_storage
from app.services.file_links import firmar_url
from app.services.file_storage import LocalFileStorage, S3FileStorage

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32
HEIC = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 32


def _como(rol: str, user_id: str | None = None, property_id: str | None = None):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id
    uid = user_id or str(uuid.uuid4())

    def override():
        return CurrentUser(user_id=uid, tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id)

    app.dependency_overrides[get_current_user] = override
    return uid


def _subir(client, contenido=JPEG, nombre="recibo.jpg", kind="pago", tipo="image/jpeg"):
    return client.post("/files", files={"file": (nombre, contenido, tipo)}, data={"kind": kind})


def _descargar(client, url: str):
    partes = urlsplit(url)
    return client.get(f"{partes.path}?{partes.query}")


# ---------- Subida ----------


@pytest.mark.parametrize(
    "contenido,tipo",
    [(JPEG, "image/jpeg"), (PNG, "image/png"), (PDF, "application/pdf"), (WEBP, "image/webp"), (HEIC, "image/heic")],
)
def test_acepta_fotos_y_pdf_y_detecta_el_tipo_por_los_bytes(client, contenido, tipo):
    # el cliente declara siempre "application/octet-stream": el tipo sale de los bytes
    respuesta = _subir(client, contenido, "archivo.bin", tipo="application/octet-stream")
    assert respuesta.status_code == 201
    archivo = respuesta.json()
    assert archivo["content_type"] == tipo
    assert archivo["size"] == len(contenido)
    assert archivo["ref"] == f"/files/{archivo['id']}"


def test_rechaza_un_svg_o_html_aunque_se_disfrace_de_imagen(client):
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    assert _subir(client, svg, "foto.png", tipo="image/png").status_code == 415
    assert _subir(client, b"<html><script>alert(1)</script></html>", "foto.jpg", tipo="image/jpeg").status_code == 415
    assert _subir(client, b"MZ\x90\x00 un ejecutable", "recibo.pdf", tipo="application/pdf").status_code == 415


def test_rechaza_un_archivo_vacio_y_uno_demasiado_grande(client, monkeypatch):
    assert _subir(client, b"").status_code == 422
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    assert _subir(client, JPEG + b"1" * 100).status_code == 413
    assert _subir(client, JPEG[:4] + b"1" * 96).status_code == 201  # justo en el límite sí pasa


def test_el_nombre_del_archivo_se_limpia_de_rutas(client):
    archivo = _subir(client, JPEG, "../../etc/pass\x00wd.jpg").json()
    assert "/" not in archivo["nombre_original"] and "\x00" not in archivo["nombre_original"]
    assert archivo["nombre_original"].endswith("wd.jpg")


def test_el_tipo_de_archivo_debe_ser_conocido(client):
    assert _subir(client, kind="cualquiera").status_code == 422


def test_quien_puede_subir_cada_tipo_de_archivo(client):
    _como("residente", property_id=str(uuid.uuid4()))
    assert _subir(client, kind="pago").status_code == 201
    assert _subir(client, kind="gasto").status_code == 403
    assert _subir(client, kind="incidencia").status_code == 403

    _como("tesorero")
    assert _subir(client, kind="gasto").status_code == 403  # solo el administrador registra gastos
    _como("admin")
    assert _subir(client, kind="gasto").status_code == 201
    _como("guardia")
    assert _subir(client, kind="incidencia").status_code == 201
    assert _subir(client, kind="gasto").status_code == 403


# ---------- Enlaces firmados ----------


def test_un_enlace_firmado_entrega_el_archivo_sin_sesion_y_con_cabeceras_seguras(client):
    _como("admin")
    archivo = _subir(client, PDF, "Factura año.pdf", kind="gasto").json()
    enlace = client.get(f"/files/{archivo['id']}/link").json()

    assert enlace["expira_en_segundos"] == settings.file_link_ttl_seconds
    app.dependency_overrides.pop(get_current_user)  # sin sesión: el enlace es la única credencial
    descarga = _descargar(client, enlace["url"])

    assert descarga.status_code == 200
    assert descarga.content == PDF
    assert descarga.headers["content-type"] == "application/pdf"
    assert descarga.headers["x-content-type-options"] == "nosniff"
    assert "filename*=UTF-8''Factura%20a%C3%B1o.pdf" in descarga.headers["content-disposition"]


def test_un_enlace_vencido_o_alterado_se_rechaza(client, monkeypatch):
    archivo = _subir(client, kind="gasto").json()
    fid = uuid.UUID(archivo["id"])

    monkeypatch.setattr(settings, "file_link_ttl_seconds", -10)
    vencido = _descargar(client, firmar_url(fid, "test"))
    assert vencido.status_code == 401 and "expiró" in vencido.json()["detail"]
    monkeypatch.undo()

    valido = firmar_url(fid, "test")
    assert _descargar(client, valido[:-3] + "abc").status_code == 401  # firma alterada
    assert client.get(f"/files/{fid}/content?t=basura").status_code == 401
    assert client.get(f"/files/{fid}/content").status_code == 422  # sin enlace


def test_un_enlace_solo_sirve_para_su_propio_archivo(client):
    uno, otro = _subir(client).json(), _subir(client).json()
    enlace_del_uno = firmar_url(uuid.UUID(uno["id"]), "test")
    token = urlsplit(enlace_del_uno).query
    assert client.get(f"/files/{otro['id']}/content?{token}").status_code == 401


def test_un_token_de_sesion_no_sirve_como_enlace_de_archivo_ni_al_reves(client):
    archivo = _subir(client).json()
    sesion = jwt.encode({"sub": "u", "tenant_id": "t", "schema": "test", "rol": "admin"}, settings.jwt_secret, algorithm="HS256")
    assert client.get(f"/files/{archivo['id']}/content?t={sesion}").status_code == 401

    enlace = urlsplit(firmar_url(uuid.UUID(archivo["id"]), "test")).query.removeprefix("t=")
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(enlace, settings.jwt_secret, algorithms=["HS256"])  # no es un token de sesión válido


def test_quien_puede_pedir_el_enlace_de_cada_archivo(client):
    admin = _como("admin")
    gasto = _subir(client, kind="gasto").json()
    pago_ajeno = _como("residente", property_id=str(uuid.uuid4()))
    pago = _subir(client, kind="pago").json()

    # un residente ve los comprobantes de gastos (transparencia), pero no el pago de otro
    otro = _como("residente", property_id=str(uuid.uuid4()))
    assert client.get(f"/files/{gasto['id']}/link").status_code == 200
    assert client.get(f"/files/{pago['id']}/link").status_code == 404

    _como("residente", user_id=pago_ajeno, property_id=str(uuid.uuid4()))
    assert client.get(f"/files/{pago['id']}/link").status_code == 200  # quien lo subió

    _como("tesorero")
    assert client.get(f"/files/{pago['id']}/link").status_code == 200  # tesorería revisa pagos
    assert admin
    assert otro and client.get(f"/files/{uuid.uuid4()}/link").status_code == 404


# ---------- Almacenamiento ----------


@pytest.mark.asyncio
async def test_el_almacenamiento_local_guarda_lee_y_borra_y_no_sale_de_su_directorio(tmp_path):
    almacen = LocalFileStorage(tmp_path)
    await almacen.save("tenant_x/abc", b"hola", "image/png")
    assert await almacen.read("tenant_x/abc") == b"hola"
    await almacen.delete("tenant_x/abc")
    with pytest.raises(FileNotFoundError):
        await almacen.read("tenant_x/abc")
    with pytest.raises(ValueError):
        await almacen.save("../fuera", b"x", "image/png")


@pytest.mark.asyncio
async def test_el_almacenamiento_s3_usa_el_bucket_cifra_y_lee_el_cuerpo():
    llamadas = []

    class ClienteFalso:
        def put_object(self, **kw):
            llamadas.append(("put", kw))

        def get_object(self, **kw):
            llamadas.append(("get", kw))
            return {"Body": SimpleNamespace(read=lambda: b"contenido")}

        def delete_object(self, **kw):
            llamadas.append(("delete", kw))

    almacen = S3FileStorage("mi-bucket", client=ClienteFalso())
    await almacen.save("t/1", b"datos", "application/pdf")
    assert await almacen.read("t/1") == b"contenido"
    await almacen.delete("t/1")

    assert llamadas[0] == (
        "put",
        {"Bucket": "mi-bucket", "Key": "t/1", "Body": b"datos", "ContentType": "application/pdf", "ServerSideEncryption": "AES256"},
    )
    assert llamadas[1] == ("get", {"Bucket": "mi-bucket", "Key": "t/1"})
    assert llamadas[2] == ("delete", {"Bucket": "mi-bucket", "Key": "t/1"})


def test_en_produccion_el_disco_local_no_se_acepta(monkeypatch):
    file_storage.set_storage(None)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "storage_backend", "local")
    with pytest.raises(RuntimeError, match="S3"):
        file_storage.get_storage()

    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "storage_s3_bucket", "")
    with pytest.raises(RuntimeError, match="STORAGE_S3_BUCKET"):
        file_storage.get_storage()


def test_en_produccion_el_disco_local_solo_se_acepta_con_el_permiso_explicito(monkeypatch, tmp_path):
    """Un despliegue en una sola máquina, con volumen persistente y respaldado, puede optar por el disco local."""
    file_storage.set_storage(None)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(settings, "storage_local_in_production", True)
    try:
        assert isinstance(file_storage.get_storage(), file_storage.LocalFileStorage)
    finally:
        file_storage.set_storage(None)
