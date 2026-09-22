"""
Nombre y logo del condominio (mostrados en el encabezado del panel): editables solo por el administrador. El
logo se sirve con su propia ruta (no por el sistema general de archivos con enlace firmado, ver files.py) porque
el encabezado lo necesita disponible todo el tiempo que dure la sesión, no solo una hora.
"""

import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str) -> None:
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


def test_get_tenant_regresa_el_nombre_sembrado_al_registrar_y_sin_logo(client):
    r = client.get("/tenant")
    assert r.status_code == 200
    body = r.json()
    assert body["nombre"] and body["tiene_logo"] is False


def test_el_admin_puede_cambiar_el_nombre(client):
    r = client.patch("/tenant", json={"nombre": "Residencial Los Encinos"})
    assert r.status_code == 200
    assert r.json()["nombre"] == "Residencial Los Encinos"
    assert client.get("/tenant").json()["nombre"] == "Residencial Los Encinos"


def test_el_nombre_se_recorta_y_no_puede_quedar_vacio(client):
    assert client.patch("/tenant", json={"nombre": "  Los Encinos  "}).json()["nombre"] == "Los Encinos"
    assert client.patch("/tenant", json={"nombre": ""}).status_code == 422
    assert client.patch("/tenant", json={"nombre": "x" * 201}).status_code == 422


def test_solo_el_admin_cambia_el_nombre_pero_cualquiera_lo_consulta(client):
    for rol in ("tesorero", "comite_aprobador", "residente", "guardia"):
        _como(rol)
        assert client.patch("/tenant", json={"nombre": "Otro"}).status_code == 403
        assert client.get("/tenant").status_code == 200


def test_subir_un_logo_lo_deja_disponible_y_se_puede_reemplazar(client):
    subida = client.post("/tenant/logo", files={"file": ("logo.jpg", JPEG, "image/jpeg")})
    assert subida.status_code == 200
    assert subida.json()["tiene_logo"] is True
    assert client.get("/tenant").json()["tiene_logo"] is True

    descarga = client.get("/tenant/logo")
    assert descarga.status_code == 200
    assert descarga.headers["content-type"] == "image/jpeg"
    assert descarga.content == JPEG

    reemplazo = client.post("/tenant/logo", files={"file": ("logo.png", PNG, "image/png")})
    assert reemplazo.status_code == 200
    otra_descarga = client.get("/tenant/logo")
    assert otra_descarga.headers["content-type"] == "image/png"
    assert otra_descarga.content == PNG  # el nuevo pisó al anterior, no quedaron los dos


def test_sin_logo_get_logo_da_404(client):
    assert client.get("/tenant/logo").status_code == 404


def test_el_logo_solo_acepta_imagenes_no_pdf_ni_basura(client):
    assert client.post("/tenant/logo", files={"file": ("x.pdf", PDF, "application/pdf")}).status_code == 415
    assert client.post("/tenant/logo", files={"file": ("x.jpg", b"no es una imagen", "image/jpeg")}).status_code == 415
    assert client.post("/tenant/logo", files={"file": ("vacio.jpg", b"", "image/jpeg")}).status_code == 422


def test_el_logo_tiene_un_limite_de_tamano(client):
    grande = b"\xff\xd8\xff\xe0" + b"\x00" * (3 * 1024 * 1024 + 1)
    r = client.post("/tenant/logo", files={"file": ("grande.jpg", grande, "image/jpeg")})
    assert r.status_code == 413


def test_el_admin_puede_borrar_el_logo(client):
    client.post("/tenant/logo", files={"file": ("logo.jpg", JPEG, "image/jpeg")})
    assert client.delete("/tenant/logo").status_code == 204
    assert client.get("/tenant").json()["tiene_logo"] is False
    assert client.get("/tenant/logo").status_code == 404
    assert client.delete("/tenant/logo").status_code == 204  # borrar dos veces no truena


def test_solo_el_admin_sube_o_borra_el_logo_pero_cualquiera_lo_ve(client):
    client.post("/tenant/logo", files={"file": ("logo.jpg", JPEG, "image/jpeg")})
    for rol in ("tesorero", "comite_aprobador", "residente", "guardia"):
        _como(rol)
        assert client.post("/tenant/logo", files={"file": ("x.jpg", JPEG, "image/jpeg")}).status_code == 403
        assert client.delete("/tenant/logo").status_code == 403
        assert client.get("/tenant/logo").status_code == 200
