"""
Dudas de los residentes sobre un aviso: un canal acotado con la administración, no un chat. La pregunta
llega solo a administración y comité, la responden el administrador y el comité aprobador, y se puede
publicar como aclaración sin nombre ni vivienda.
"""

import uuid
from datetime import timedelta

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.reglamento_service import hoy_local


def _como(rol: str, property_id: str | None = None, user_id: str | None = None) -> str:
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id
    uid = user_id or str(uuid.uuid4())

    def override():
        return CurrentUser(user_id=uid, tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id)

    app.dependency_overrides[get_current_user] = override
    return uid


def _condominio(client):
    """Dos viviendas y un aviso publicado que admite dudas."""
    casa1 = client.post("/properties", json={"identificador": "Casa 1"}).json()["id"]
    casa2 = client.post("/properties", json={"identificador": "Casa 2"}).json()["id"]
    aviso = client.post(
        "/announcements", json={"titulo": "Corte de agua", "contenido": "El jueves de 10 a 2.", "permite_dudas": True}
    ).json()
    return casa1, casa2, aviso["id"]


def _preguntar(client, aviso_id, texto="¿Habrá agua en la caseta?"):
    return client.post(f"/announcements/{aviso_id}/questions", json={"texto": texto})


# ---------- Configuración del aviso ----------


def test_las_dudas_de_un_aviso_nuevo_siguen_el_valor_por_defecto_del_reglamento(client):
    sin_decir = client.post("/announcements", json={"titulo": "A", "contenido": "x"}).json()
    assert (sin_decir["permite_dudas"], sin_decir["dudas_abiertas"]) == (False, False)  # apagadas por defecto

    client.patch("/tenant/reglamento", json={"dudas_en_avisos_por_defecto": True})
    por_defecto = client.post("/announcements", json={"titulo": "B", "contenido": "x"}).json()
    assert por_defecto["permite_dudas"] is True and por_defecto["dudas_abiertas"] is True

    explicito = client.post("/announcements", json={"titulo": "C", "contenido": "x", "permite_dudas": False}).json()
    assert explicito["permite_dudas"] is False  # lo que diga el administrador al publicar manda


def test_las_dudas_se_pueden_cerrar_con_una_fecha_limite(client):
    ayer, hoy = (hoy_local() - timedelta(days=1)).isoformat(), hoy_local().isoformat()
    vencido = client.post("/announcements", json={"titulo": "A", "contenido": "x", "permite_dudas": True, "dudas_hasta": ayer}).json()
    vigente = client.post("/announcements", json={"titulo": "B", "contenido": "x", "permite_dudas": True, "dudas_hasta": hoy}).json()

    assert vencido["dudas_abiertas"] is False and vencido["permite_dudas"] is True
    assert vigente["dudas_abiertas"] is True  # el día límite todavía cuenta


def test_sin_dudas_no_se_guarda_un_plazo_y_se_pueden_activar_despues(client):
    aviso = client.post(
        "/announcements", json={"titulo": "A", "contenido": "x", "permite_dudas": False, "dudas_hasta": "2030-01-01"}
    ).json()
    assert aviso["dudas_hasta"] is None

    activado = client.patch(f"/announcements/{aviso['id']}", json={"permite_dudas": True, "dudas_hasta": "2030-01-01"}).json()
    assert (activado["permite_dudas"], activado["dudas_hasta"]) == (True, "2030-01-01")
    apagado = client.patch(f"/announcements/{aviso['id']}", json={"permite_dudas": False}).json()
    assert (apagado["permite_dudas"], apagado["dudas_hasta"]) == (False, None)


def test_el_listado_de_avisos_dice_si_admiten_dudas(client):
    _condominio(client)
    _como("residente", property_id=str(uuid.uuid4()))
    assert client.get("/announcements").json()[0]["dudas_abiertas"] is True


# ---------- Preguntar ----------


def test_el_residente_manda_una_duda_y_queda_abierta(client):
    casa1, _, aviso = _condominio(client)
    _como("residente", property_id=casa1)

    respuesta = _preguntar(client, aviso)

    assert respuesta.status_code == 201
    duda = respuesta.json()
    assert (duda["estado"], duda["propia"], duda["publica"], duda["respuesta"]) == ("abierta", True, False, None)
    assert duda["aviso_titulo"] == "Corte de agua"


def test_no_se_puede_preguntar_en_un_aviso_sin_dudas_ni_fuera_de_plazo(client):
    casa1, _, _ = _condominio(client)
    sin_dudas = client.post("/announcements", json={"titulo": "S", "contenido": "x"}).json()["id"]
    cerrado = client.post(
        "/announcements",
        json={"titulo": "C", "contenido": "x", "permite_dudas": True, "dudas_hasta": (hoy_local() - timedelta(days=1)).isoformat()},
    ).json()["id"]
    _como("residente", property_id=casa1)

    a = _preguntar(client, sin_dudas)
    b = _preguntar(client, cerrado)

    assert a.status_code == 409 and "no recibe dudas" in a.json()["detail"]
    assert b.status_code == 409 and "plazo" in b.json()["detail"]


def test_tope_de_tres_dudas_abiertas_por_vivienda_y_se_libera_al_responderse(client):
    casa1, casa2, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    ids = [_preguntar(client, aviso, f"Duda {i}").json()["id"] for i in range(3)]

    cuarta = _preguntar(client, aviso, "Duda 4")
    assert cuarta.status_code == 409 and "3 dudas sin responder" in cuarta.json()["detail"]

    _como("residente", property_id=casa2)
    assert _preguntar(client, aviso).status_code == 201  # el tope es por vivienda

    _como("admin")
    client.post(f"/announcement-questions/{ids[0]}/answer", json={"respuesta": "Sí."})
    _como("residente", property_id=casa1)
    assert _preguntar(client, aviso, "Duda 4").status_code == 201


def test_la_duda_debe_tener_texto_y_no_pasar_de_500_caracteres(client):
    casa1, _, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    assert _preguntar(client, aviso, "").status_code == 422
    assert _preguntar(client, aviso, "   ").status_code == 422
    assert _preguntar(client, aviso, "x" * 501).status_code == 422
    assert _preguntar(client, aviso, "x" * 500).status_code == 201


def test_solo_un_residente_con_vivienda_pregunta_y_un_aviso_sin_publicar_no_existe_para_el(client):
    casa1, _, aviso = _condominio(client)
    _como("guardia")
    assert _preguntar(client, aviso).status_code == 400

    _como("admin")
    futuro = client.post(
        "/announcements",
        json={"titulo": "F", "contenido": "x", "permite_dudas": True, "fecha_publicacion": "2099-01-01T00:00:00"},
    ).json()["id"]
    _como("residente", property_id=casa1)
    assert _preguntar(client, futuro).status_code == 404
    assert _preguntar(client, str(uuid.uuid4())).status_code == 404


# ---------- Quién ve qué ----------


def test_una_duda_privada_solo_la_ven_su_vivienda_y_la_administracion(client):
    casa1, casa2, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    _preguntar(client, aviso, "¿Cuánto durará?")

    assert len(client.get(f"/announcements/{aviso}/questions").json()) == 1  # la propia
    _como("residente", property_id=casa2)
    assert client.get(f"/announcements/{aviso}/questions").json() == []  # un vecino no la ve
    _como("guardia")
    assert client.get(f"/announcements/{aviso}/questions").json() == []

    for rol in ("admin", "comite_lectura", "comite_aprobador"):
        _como(rol)
        vistas = client.get(f"/announcements/{aviso}/questions").json()
        assert [(d["texto"], d["vivienda"]) for d in vistas] == [("¿Cuánto durará?", "Casa 1")], rol


def test_publicada_como_aclaracion_todos_la_ven_sin_nombre_ni_vivienda(client):
    casa1, casa2, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    duda = _preguntar(client, aviso, "¿Aplica a la torre B?").json()
    _como("admin")
    client.post(f"/announcement-questions/{duda['id']}/answer", json={"respuesta": "Solo torres A y C.", "publicar": True})

    _como("residente", property_id=casa2)
    ajena = client.get(f"/announcements/{aviso}/questions").json()[0]
    assert (ajena["texto"], ajena["respuesta"]) == ("¿Aplica a la torre B?", "Solo torres A y C.")
    assert (ajena["propia"], ajena["vivienda"], ajena["respuesta_nueva"]) == (False, None, False)
    _como("guardia")
    assert len(client.get(f"/announcements/{aviso}/questions").json()) == 1


def test_una_respuesta_no_publicada_no_es_visible_para_los_demas(client):
    casa1, casa2, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    duda = _preguntar(client, aviso).json()
    _como("admin")
    client.post(f"/announcement-questions/{duda['id']}/answer", json={"respuesta": "Sí."})

    _como("residente", property_id=casa2)
    assert client.get(f"/announcements/{aviso}/questions").json() == []


def test_retirar_una_aclaracion_la_oculta_de_nuevo(client):
    casa1, casa2, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    duda = _preguntar(client, aviso).json()
    _como("admin")
    client.post(f"/announcement-questions/{duda['id']}/answer", json={"respuesta": "Sí.", "publicar": True})
    client.patch(f"/announcement-questions/{duda['id']}", json={"publica": False})

    _como("residente", property_id=casa2)
    assert client.get(f"/announcements/{aviso}/questions").json() == []


# ---------- Responder ----------


def test_administrador_y_comite_aprobador_responden_pero_el_comite_de_lectura_no(client):
    casa1, _, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    ids = [_preguntar(client, aviso, f"Duda {i}").json()["id"] for i in range(3)]

    _como("comite_lectura")
    assert client.post(f"/announcement-questions/{ids[0]}/answer", json={"respuesta": "x"}).status_code == 403
    _como("residente", property_id=casa1)
    assert client.post(f"/announcement-questions/{ids[0]}/answer", json={"respuesta": "x"}).status_code == 403
    for rol, duda in (("admin", ids[0]), ("comite_aprobador", ids[1])):
        _como(rol)
        assert client.post(f"/announcement-questions/{duda}/answer", json={"respuesta": "Respondida"}).status_code == 200, rol


def test_una_duda_se_responde_una_sola_vez_y_despues_solo_se_corrige(client):
    casa1, _, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    duda = _preguntar(client, aviso).json()["id"]

    _como("admin")
    assert client.patch(f"/announcement-questions/{duda}", json={"publica": True}).status_code == 409  # aún sin respuesta
    assert client.post(f"/announcement-questions/{duda}/answer", json={"respuesta": ""}).status_code == 422
    assert client.post(f"/announcement-questions/{duda}/answer", json={"respuesta": "x" * 1001}).status_code == 422
    assert client.post(f"/announcement-questions/{duda}/answer", json={"respuesta": "Sí."}).status_code == 200
    assert client.post(f"/announcement-questions/{duda}/answer", json={"respuesta": "Otra"}).status_code == 409
    corregida = client.patch(f"/announcement-questions/{duda}", json={"respuesta": "Sí, hay cisterna."}).json()
    assert corregida["respuesta"] == "Sí, hay cisterna."
    assert client.post(f"/announcement-questions/{uuid.uuid4()}/answer", json={"respuesta": "x"}).status_code == 404
    assert client.patch(f"/announcement-questions/{uuid.uuid4()}", json={"publica": True}).status_code == 404


# ---------- Bandeja de la administración ----------


def test_la_bandeja_lista_las_dudas_sin_responder_de_todos_los_avisos_las_mas_viejas_primero(client):
    casa1, casa2, aviso = _condominio(client)
    otro = client.post("/announcements", json={"titulo": "Junta", "contenido": "x", "permite_dudas": True}).json()["id"]
    _como("residente", property_id=casa1)
    primera = _preguntar(client, aviso, "Primera").json()
    _como("residente", property_id=casa2)
    _preguntar(client, otro, "Segunda")
    _como("admin")
    client.post(f"/announcement-questions/{primera['id']}/answer", json={"respuesta": "Listo."})

    _como("comite_lectura")
    pendientes = client.get("/announcement-questions/pending").json()
    assert [(d["texto"], d["aviso_titulo"], d["vivienda"]) for d in pendientes] == [("Segunda", "Junta", "Casa 2")]
    respondidas = client.get("/announcement-questions/answered").json()
    assert [(d["texto"], d["respuesta"]) for d in respondidas] == [("Primera", "Listo.")]


def test_la_bandeja_es_solo_para_administracion_y_comite(client):
    _condominio(client)
    for rol in ("residente", "guardia", "tesorero"):
        _como(rol, property_id=str(uuid.uuid4()) if rol == "residente" else None)
        assert client.get("/announcement-questions/pending").status_code == 403, rol
        assert client.get("/announcement-questions/answered").status_code == 403, rol


# ---------- El aviso dentro de la app ----------


def test_el_residente_ve_sus_respuestas_como_nuevas_hasta_que_las_abre(client):
    casa1, casa2, aviso = _condominio(client)
    _como("residente", property_id=casa1)
    duda = _preguntar(client, aviso).json()
    assert client.get("/announcement-questions/mine").json()[0]["respuesta_nueva"] is False  # aún sin respuesta

    _como("admin")
    client.post(f"/announcement-questions/{duda['id']}/answer", json={"respuesta": "Sí."})
    _como("residente", property_id=casa1)
    mias = client.get("/announcement-questions/mine").json()
    assert (mias[0]["respuesta"], mias[0]["respuesta_nueva"]) == ("Sí.", True)

    assert client.post("/announcement-questions/mine/seen").status_code == 204
    assert client.get("/announcement-questions/mine").json()[0]["respuesta_nueva"] is False

    _como("admin")  # corregir la respuesta vuelve a marcarla como nueva
    client.patch(f"/announcement-questions/{duda['id']}", json={"respuesta": "Sí, hay cisterna."})
    _como("residente", property_id=casa1)
    assert client.get("/announcement-questions/mine").json()[0]["respuesta_nueva"] is True

    _como("residente", property_id=casa2)  # un vecino no ve ni marca las de otro
    assert client.get("/announcement-questions/mine").json() == []


def test_mis_dudas_y_marcar_vistas_sin_vivienda(client):
    _como("guardia")
    assert client.get("/announcement-questions/mine").json() == []
    assert client.post("/announcement-questions/mine/seen").status_code == 400
