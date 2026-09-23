"""
F2-18: gestión mínima de cuentas de personal — sin esto no había forma de
designar un aprobador de amenidades (F2-17) que no fuera el admin sembrado
al aprovisionar el tenant. Ningún endpoint existía para esto antes.
"""

import uuid

import pytest
from sqlalchemy import select

from app.api.deps import get_current_user
from app.main import app
from app.models.user_lookup import UserLookup
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def test_admin_puede_crear_un_usuario_con_rol_comite_aprobador(client):
    response = client.post(
        "/users", json={"email": "aprobador@condo.mx", "password": "clave-temporal-123", "rol": "comite_aprobador"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "aprobador@condo.mx"
    assert body["rol"] == "comite_aprobador"
    assert "password" not in body
    assert "password_hash" not in body


def test_password_corta_es_rechazada(client):
    response = client.post("/users", json={"email": "x@condo.mx", "password": "corta", "rol": "guardia"})
    assert response.status_code == 422


def test_no_se_puede_repetir_el_email(client):
    client.post("/users", json={"email": "vocero@condo.mx", "password": "clave-123456", "rol": "vocero"})
    response = client.post("/users", json={"email": "vocero@condo.mx", "password": "otra-clave", "rol": "guardia"})
    assert response.status_code == 409


def test_list_users_filtra_por_rol(client):
    client.post("/users", json={"email": "aprobador1@condo.mx", "password": "clave-123456", "rol": "comite_aprobador"})
    client.post("/users", json={"email": "aprobador2@condo.mx", "password": "clave-123456", "rol": "comite_aprobador"})
    client.post("/users", json={"email": "vocero@condo.mx", "password": "clave-123456", "rol": "vocero"})

    response = client.get("/users", params={"rol": "comite_aprobador"})
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert emails == {"aprobador1@condo.mx", "aprobador2@condo.mx"}


def test_list_users_sin_filtro_regresa_todos(client):
    client.post("/users", json={"email": "aprobador@condo.mx", "password": "clave-123456", "rol": "comite_aprobador"})
    client.post("/users", json={"email": "vocero@condo.mx", "password": "clave-123456", "rol": "vocero"})

    response = client.get("/users")
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_crear_usuario_registra_en_user_lookup(client):
    """
    /auth/login resuelve el tenant de un email consultando user_lookup (schema
    de control) ANTES de siquiera abrir la sesión del tenant — sin ese
    registro, la cuenta nueva jamás podría iniciar sesión aunque exista en
    user_account. No se puede probar /auth/login de punta a punta aquí: usa
    control_session()/tenant_session() directamente (no get_tenant_db), que
    esta suite no sobreescribe — ningún otro test del proyecto lo hace
    tampoco, es un hueco preexistente del fixture, no de este cambio. Se
    verifica en cambio el efecto concreto que sí depende de create_user():
    que el registro en user_lookup exista con el tenant_id y user_id correctos.
    """
    creado = client.post(
        "/users", json={"email": "tesorero@condo.mx", "password": "clave-123456", "rol": "tesorero"}
    ).json()

    async with client.db_session_factory() as db:
        lookup = (await db.execute(select(UserLookup).where(UserLookup.email == "tesorero@condo.mx"))).scalar_one()

    assert str(lookup.user_id) == creado["id"]
    assert str(lookup.tenant_id) == _tenant_id()


def test_no_admin_no_puede_crear_ni_listar_usuarios(client):
    _como("guardia")
    assert client.post("/users", json={"email": "x@x.com", "password": "clave-123456", "rol": "guardia"}).status_code == 403
    assert client.get("/users").status_code == 403


def test_admin_puede_crear_un_residente_con_property_id(client):
    """
    Bug real (F1-29): UserAccountCreate no declaraba property_id, así que
    Pydantic lo descartaba en silencio y ningún residente creado por este
    endpoint quedaba asociado a una vivienda — la app residente completa
    quedaba inalcanzable para cualquier tenant nuevo. Se descubrió al
    construir la prueba de punta a punta del flujo de cobro.
    """
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()

    response = client.post(
        "/users",
        json={
            "email": "residente@condo.mx",
            "password": "clave-temporal-123",
            "rol": "residente",
            "property_id": prop["id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["property_id"] == prop["id"]


# ---------- Editar y dar de baja cuentas ----------


def _crear(client, email, rol="tesorero", **extra):
    return client.post("/users", json={"email": email, "password": "clave-123456", "rol": rol, **extra}).json()


def _soy(user_id: str):
    """Actúa como esa cuenta (para probar «no puedes editarte a ti mismo»)."""
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=user_id, tenant_id=tenant_id, schema_name="test", rol="admin", property_id=None)

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_cambiar_el_correo_actualiza_la_cuenta_y_el_user_lookup(client):
    creado = _crear(client, "viejo@condo.mx")

    r = client.patch(f"/users/{creado['id']}", json={"email": "nuevo@condo.mx"})
    assert r.status_code == 200 and r.json()["email"] == "nuevo@condo.mx"

    async with client.db_session_factory() as db:
        filas = (await db.execute(select(UserLookup).where(UserLookup.user_id == uuid.UUID(creado["id"])))).scalars().all()
    assert [f.email for f in filas] == ["nuevo@condo.mx"]  # el login busca por aquí: si no cambia, la cuenta queda inaccesible


def test_no_se_puede_tomar_el_correo_de_otra_cuenta(client):
    _crear(client, "ocupado@condo.mx")
    otra = _crear(client, "libre@condo.mx")
    assert client.patch(f"/users/{otra['id']}", json={"email": "ocupado@condo.mx"}).status_code == 409


def test_repetir_su_propio_correo_no_es_conflicto(client):
    creado = _crear(client, "igual@condo.mx")
    assert client.patch(f"/users/{creado['id']}", json={"email": "igual@condo.mx", "rol": "vocero"}).status_code == 200


@pytest.mark.asyncio
async def test_cambiar_la_contrasena_guarda_el_nuevo_hash(client):
    from app.core.security import verify_password
    from app.models.user import UserAccount

    creado = _crear(client, "clave@condo.mx")
    assert client.patch(f"/users/{creado['id']}", json={"password": "otra-clave-987"}).status_code == 200

    async with client.db_session_factory() as db:
        user = await db.get(UserAccount, uuid.UUID(creado["id"]))
    assert verify_password("otra-clave-987", user.password_hash)
    assert not verify_password("clave-123456", user.password_hash)


def test_una_contrasena_corta_al_editar_se_rechaza(client):
    creado = _crear(client, "corta@condo.mx")
    assert client.patch(f"/users/{creado['id']}", json={"password": "corta"}).status_code == 422


@pytest.mark.asyncio
async def test_cambiar_la_contrasena_apaga_debe_cambiar_password(client):
    """
    Alta por /signup: el admin nace con debe_cambiar_password=True (contraseña temporal = nombre del
    condominio, ver provisioning.py) — en cuanto fija una contraseña real vía PATCH /users/{id}, esa bandera
    debe apagarse; si no, el panel seguiría pidiéndole cambiarla para siempre.
    """
    from app.models.user import UserAccount

    creado = _crear(client, "temporal@condo.mx")
    async with client.db_session_factory() as db:
        user = await db.get(UserAccount, uuid.UUID(creado["id"]))
        user.debe_cambiar_password = True
        await db.commit()

    assert client.patch(f"/users/{creado['id']}", json={"password": "clave-definitiva-1"}).status_code == 200

    async with client.db_session_factory() as db:
        user = await db.get(UserAccount, uuid.UUID(creado["id"]))
    assert user.debe_cambiar_password is False


def test_crear_usuario_acepta_nombre_y_telefono(client):
    response = client.post(
        "/users",
        json={
            "email": "conNombre@condo.mx", "password": "clave-123456", "rol": "tesorero",
            "nombre": "Patricia Gómez", "telefono": "5555555555",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["nombre"] == "Patricia Gómez"
    assert body["telefono"] == "5555555555"


def test_cambiar_el_rol_y_la_vivienda(client):
    casa = client.post("/properties", json={"identificador": "Casa 9"}).json()
    creado = _crear(client, "vecino@condo.mx", "tesorero")

    r = client.patch(f"/users/{creado['id']}", json={"rol": "residente", "property_id": casa["id"]})
    assert r.status_code == 200
    assert (r.json()["rol"], r.json()["property_id"]) == ("residente", casa["id"])


def test_un_residente_no_puede_quedarse_sin_vivienda(client):
    casa = client.post("/properties", json={"identificador": "Casa 9"}).json()
    creado = _crear(client, "vecino@condo.mx", "residente", property_id=casa["id"])

    assert client.patch(f"/users/{creado['id']}", json={"property_id": None}).status_code == 422
    assert client.patch(f"/users/{creado['id']}", json={"rol": "residente", "property_id": str(uuid.uuid4())}).status_code == 404


def test_quitar_la_vivienda_a_quien_no_es_residente_si_se_puede(client):
    casa = client.post("/properties", json={"identificador": "Casa 9"}).json()
    creado = _crear(client, "guardia@condo.mx", "guardia", property_id=casa["id"])

    r = client.patch(f"/users/{creado['id']}", json={"property_id": None})
    assert r.status_code == 200 and r.json()["property_id"] is None


def test_editar_una_cuenta_que_no_existe_es_404(client):
    assert client.patch(f"/users/{uuid.uuid4()}", json={"rol": "vocero"}).status_code == 404


def test_nadie_puede_cambiarse_su_propio_rol(client):
    yo = _crear(client, "admin1@condo.mx", "admin")
    _crear(client, "admin2@condo.mx", "admin")
    _soy(yo["id"])

    assert client.patch(f"/users/{yo['id']}", json={"rol": "vocero"}).status_code == 409


def test_el_ultimo_administrador_no_se_puede_degradar(client):
    unico = _crear(client, "admin@condo.mx", "admin")

    r = client.patch(f"/users/{unico['id']}", json={"rol": "vocero"})
    assert r.status_code == 409 and "único administrador" in r.json()["detail"]


def test_con_dos_administradores_uno_si_se_puede_degradar(client):
    _crear(client, "admin1@condo.mx", "admin")
    otro = _crear(client, "admin2@condo.mx", "admin")

    assert client.patch(f"/users/{otro['id']}", json={"rol": "tesorero"}).status_code == 200


def test_solo_el_admin_edita_o_elimina_cuentas(client):
    creado = _crear(client, "cuenta@condo.mx")
    _como("tesorero")

    assert client.patch(f"/users/{creado['id']}", json={"rol": "vocero"}).status_code == 403
    assert client.delete(f"/users/{creado['id']}").status_code == 403


@pytest.mark.asyncio
async def test_eliminar_una_cuenta_la_quita_tambien_del_user_lookup(client):
    from app.models.user import UserAccount

    creado = _crear(client, "baja@condo.mx")

    assert client.delete(f"/users/{creado['id']}").status_code == 204
    assert [u["email"] for u in client.get("/users").json()] == []
    async with client.db_session_factory() as db:
        assert await db.get(UserAccount, uuid.UUID(creado["id"])) is None
        assert (await db.execute(select(UserLookup).where(UserLookup.email == "baja@condo.mx"))).scalar_one_or_none() is None
    # el correo queda libre para otra cuenta
    assert client.post("/users", json={"email": "baja@condo.mx", "password": "clave-123456", "rol": "guardia"}).status_code == 201


def test_no_se_puede_eliminar_la_propia_cuenta_ni_al_ultimo_admin(client):
    unico = _crear(client, "admin@condo.mx", "admin")
    _soy(unico["id"])
    assert client.delete(f"/users/{unico['id']}").status_code == 409

    _soy(str(uuid.uuid4()))  # otra persona intentando: sigue siendo el único administrador
    r = client.delete(f"/users/{unico['id']}")
    assert r.status_code == 409 and "único administrador" in r.json()["detail"]


def test_eliminar_una_cuenta_que_no_existe_es_404(client):
    assert client.delete(f"/users/{uuid.uuid4()}").status_code == 404


# ---------- Editar y dar de baja cuentas ----------


def _crear(client, email, rol="tesorero", **extra):
    return client.post("/users", json={"email": email, "password": "clave-123456", "rol": rol, **extra}).json()


def _como_usuario(user_id: str, rol: str = "admin"):
    """Actúa como una cuenta concreta (para las guardas «no tú mismo»)."""
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(user_id=user_id, tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


@pytest.mark.asyncio
async def test_editar_el_correo_actualiza_tambien_user_lookup(client):
    creado = _crear(client, "viejo@condo.mx")

    r = client.patch(f"/users/{creado['id']}", json={"email": "nuevo@condo.mx"})

    assert r.status_code == 200 and r.json()["email"] == "nuevo@condo.mx"
    async with client.db_session_factory() as db:
        lookups = (await db.execute(select(UserLookup).where(UserLookup.user_id == uuid.UUID(creado["id"])))).scalars().all()
    assert [lk.email for lk in lookups] == ["nuevo@condo.mx"]  # el login resuelve el tenant por este correo


def test_no_se_puede_editar_a_un_correo_que_ya_existe(client):
    _crear(client, "a@condo.mx")
    b = _crear(client, "b@condo.mx")

    r = client.patch(f"/users/{b['id']}", json={"email": "a@condo.mx"})

    assert r.status_code == 409


def test_mandar_el_mismo_correo_no_es_un_conflicto(client):
    a = _crear(client, "a@condo.mx")
    assert client.patch(f"/users/{a['id']}", json={"email": "a@condo.mx", "rol": "tesorero"}).status_code == 200


@pytest.mark.asyncio
async def test_cambiar_la_contrasena_guarda_un_hash_nuevo_y_valida_el_largo(client):
    from app.core.security import verify_password
    from app.models.user import UserAccount

    creado = _crear(client, "t@condo.mx")

    assert client.patch(f"/users/{creado['id']}", json={"password": "corta"}).status_code == 422
    assert client.patch(f"/users/{creado['id']}", json={"password": "clave-nueva-987"}).status_code == 200

    async with client.db_session_factory() as db:
        fila = await db.get(UserAccount, uuid.UUID(creado["id"]))
    assert verify_password("clave-nueva-987", fila.password_hash)
    assert not verify_password("clave-123456", fila.password_hash)


def test_solo_cambia_lo_que_se_manda(client):
    creado = _crear(client, "t@condo.mx", rol="tesorero")
    r = client.patch(f"/users/{creado['id']}", json={"rol": "vocero"}).json()
    assert (r["email"], r["rol"]) == ("t@condo.mx", "vocero")


def test_un_residente_necesita_vivienda_y_se_le_puede_cambiar(client):
    v1 = client.post("/properties", json={"identificador": "Casa 1"}).json()
    v2 = client.post("/properties", json={"identificador": "Casa 2"}).json()
    res = _crear(client, "vecino@condo.mx", rol="residente", property_id=v1["id"])

    assert client.patch(f"/users/{res['id']}", json={"property_id": v2["id"]}).json()["property_id"] == v2["id"]
    assert client.patch(f"/users/{res['id']}", json={"property_id": None}).status_code == 422  # quedaría sin vivienda
    assert client.patch(f"/users/{res['id']}", json={"property_id": str(uuid.uuid4())}).status_code == 404


def test_pasar_a_alguien_a_residente_sin_vivienda_se_rechaza(client):
    t = _crear(client, "t@condo.mx", rol="tesorero")
    assert client.patch(f"/users/{t['id']}", json={"rol": "residente"}).status_code == 422
    v = client.post("/properties", json={"identificador": "Casa 1"}).json()
    r = client.patch(f"/users/{t['id']}", json={"rol": "residente", "property_id": v["id"]})
    assert r.status_code == 200 and r.json()["rol"] == "residente"


def test_quitar_la_vivienda_a_un_no_residente_es_valido(client):
    v = client.post("/properties", json={"identificador": "Casa 1"}).json()
    t = _crear(client, "t@condo.mx", rol="tesorero", property_id=v["id"])
    r = client.patch(f"/users/{t['id']}", json={"property_id": None})
    assert r.status_code == 200 and r.json()["property_id"] is None


def test_no_puedes_cambiarte_el_rol_a_ti_mismo(client):
    otro_admin = _crear(client, "otro@condo.mx", rol="admin")
    yo = _crear(client, "yo@condo.mx", rol="admin")
    _como_usuario(yo["id"])

    assert client.patch(f"/users/{yo['id']}", json={"rol": "tesorero"}).status_code == 409
    assert client.patch(f"/users/{otro_admin['id']}", json={"rol": "tesorero"}).status_code == 200  # a otro sí


def test_no_se_puede_degradar_al_unico_administrador(client):
    unico = _crear(client, "unico@condo.mx", rol="admin")
    _como_usuario(str(uuid.uuid4()))  # otra sesión de admin (p. ej. soporte)
    assert client.patch(f"/users/{unico['id']}", json={"rol": "tesorero"}).status_code == 409


def test_editar_una_cuenta_inexistente_es_404(client):
    assert client.patch(f"/users/{uuid.uuid4()}", json={"rol": "vocero"}).status_code == 404


def test_solo_el_admin_edita_y_elimina_cuentas(client):
    t = _crear(client, "t@condo.mx")
    for rol in ("tesorero", "comite_aprobador", "residente", "guardia"):
        _como(rol)
        assert client.patch(f"/users/{t['id']}", json={"rol": "vocero"}).status_code == 403
        assert client.delete(f"/users/{t['id']}").status_code == 403


@pytest.mark.asyncio
async def test_eliminar_una_cuenta_la_quita_tambien_de_user_lookup(client):
    from app.models.user import UserAccount

    t = _crear(client, "baja@condo.mx")

    assert client.delete(f"/users/{t['id']}").status_code == 204

    async with client.db_session_factory() as db:
        assert await db.get(UserAccount, uuid.UUID(t["id"])) is None
        assert (await db.execute(select(UserLookup).where(UserLookup.email == "baja@condo.mx"))).scalar_one_or_none() is None
    assert client.delete(f"/users/{t['id']}").status_code == 404
    assert client.post("/users", json={"email": "baja@condo.mx", "password": "clave-123456", "rol": "guardia"}).status_code == 201


def test_no_puedes_eliminarte_ni_eliminar_al_unico_admin(client):
    yo = _crear(client, "yo@condo.mx", rol="admin")
    _como_usuario(yo["id"])
    assert client.delete(f"/users/{yo['id']}").status_code == 409  # a ti mismo

    _como_usuario(str(uuid.uuid4()))
    assert client.delete(f"/users/{yo['id']}").status_code == 409  # el único admin

    otro = _crear(client, "otro@condo.mx", rol="admin")
    assert client.delete(f"/users/{otro['id']}").status_code == 204  # con dos admins, uno sí se puede dar de baja
