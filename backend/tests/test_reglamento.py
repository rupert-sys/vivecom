"""
Reglas del reglamento interior por condominio (modelo ReglamentoConfig).
Fuente: Reglamento Interior del Condominio Arequipa, modificado el 18-ene-2026.
"""

import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _tenant_id() -> str:
    return app.dependency_overrides[get_current_user]().tenant_id


def _como(rol: str, property_id: str | None = None):
    tenant_id = _tenant_id()

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id
        )

    app.dependency_overrides[get_current_user] = override


REGLAS_AREQUIPA = {
    "dia_limite_pago": 5,
    "recargo_porcentaje": 0.05,
    "recargo_modalidad": "mensual_sobre_saldo",
    "acepta_pago_efectivo": True,
    "morosos_sin_voto": True,
    "morosos_sin_areas_comunes": True,
    "gasto_umbral_asamblea": 10000,
    "cotizaciones_minimas": 3,
    "cajones_visitas": 7,
}


def test_por_default_el_reglamento_reproduce_las_reglas_globales_de_siempre(client):
    body = client.get("/tenant/reglamento").json()
    assert body["recargo_porcentaje"] == 0.10
    assert body["recargo_modalidad"] == "unico"
    assert body["dia_recargo"] == 6
    assert body["acepta_pago_efectivo"] is False
    assert body["morosos_sin_voto"] is False
    assert body["gasto_umbral_asamblea"] is None


def test_el_admin_configura_las_reglas_de_su_reglamento(client):
    response = client.patch("/tenant/reglamento", json=REGLAS_AREQUIPA)
    assert response.status_code == 200
    body = response.json()
    assert body["recargo_porcentaje"] == 0.05
    assert body["recargo_modalidad"] == "mensual_sobre_saldo"
    assert body["cajones_visitas"] == 7

    # persiste, y un PATCH parcial no pisa lo que no se mandó
    client.patch("/tenant/reglamento", json={"cajones_visitas": 9})
    body = client.get("/tenant/reglamento").json()
    assert body["cajones_visitas"] == 9
    assert body["recargo_porcentaje"] == 0.05


def test_se_puede_quitar_el_umbral_de_gastos(client):
    client.patch("/tenant/reglamento", json={"gasto_umbral_asamblea": 10000})
    client.patch("/tenant/reglamento", json={"gasto_umbral_asamblea": None})
    assert client.get("/tenant/reglamento").json()["gasto_umbral_asamblea"] is None


def test_solo_el_admin_cambia_el_reglamento_pero_cualquiera_lo_lee(client):
    _como("residente", property_id=str(uuid.uuid4()))
    assert client.get("/tenant/reglamento").status_code == 200
    assert client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True}).status_code == 403


def test_rechaza_valores_fuera_de_rango(client):
    assert client.patch("/tenant/reglamento", json={"recargo_porcentaje": 5}).status_code == 422
    assert client.patch("/tenant/reglamento", json={"recargo_modalidad": "otro"}).status_code == 422
    assert client.patch("/tenant/reglamento", json={"dia_limite_pago": 40}).status_code == 422


# ---------- Recargo mensual sobre saldos insolutos (Art. 9 I) ----------


def _crear_cargo_de_septiembre(client, monto=750.0):
    client.post("/properties", json={"identificador": "Casa 1"})
    client.post("/fees", json={"monto": monto, "periodicidad": "mensual", "activa_desde": "2026-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})


def _deuda(client) -> float:
    prop = client.get("/properties").json()[0]
    return client.get(f"/properties/{prop['id']}/statement").json()["deuda_total"]


def _correr(client, hoy: str) -> int:
    return client.post("/fees/apply-late-surcharges", params={"hoy": hoy}).json()["cargos_marcados_vencidos"]


def test_recargo_mensual_se_acumula_cada_mes_que_sigue_sin_pagarse(client):
    client.patch("/tenant/reglamento", json=REGLAS_AREQUIPA)
    _crear_cargo_de_septiembre(client, monto=750.0)

    assert _correr(client, "2026-09-05") == 0  # dentro de los 5 días para pagar
    assert _deuda(client) == 750.0

    assert _correr(client, "2026-09-06") == 1  # 5% de $750 = $37.50
    assert _deuda(client) == 787.50

    assert _correr(client, "2026-10-05") == 0  # aún no llega el día 6 del mes siguiente
    assert _deuda(client) == 787.50

    assert _correr(client, "2026-10-06") == 1  # segundo mes: 2 × 37.50
    assert _deuda(client) == 825.0

    assert _correr(client, "2026-11-06") == 1  # tercer mes
    assert _deuda(client) == 862.50


def test_correr_el_job_dos_veces_el_mismo_dia_no_duplica_el_recargo(client):
    client.patch("/tenant/reglamento", json=REGLAS_AREQUIPA)
    _crear_cargo_de_septiembre(client, monto=750.0)

    _correr(client, "2026-10-06")
    assert _correr(client, "2026-10-06") == 0
    assert _deuda(client) == 825.0


def test_el_recargo_unico_por_default_no_se_acumula(client):
    _crear_cargo_de_septiembre(client, monto=1000.0)
    _correr(client, "2026-09-06")
    _correr(client, "2026-11-06")
    assert _deuda(client) == 1100.0  # 10% una sola vez
