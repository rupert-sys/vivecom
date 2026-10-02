"""
F0-12: caja chica y caja grande — efectivo físico que administra tesorería, con historial de
movimientos (ingreso/egreso). El saldo se calcula del historial, no se guarda aparte.
"""

import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _como(rol: str) -> None:
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def _movimiento(**extra):
    base = {"caja": "chica", "tipo": "ingreso", "monto": 500, "motivo": "Fondo inicial", "fecha": "2026-09-01"}
    base.update(extra)
    return base


def test_tesoreria_registra_un_ingreso_y_el_saldo_lo_refleja(client):
    _como("tesorero")
    creado = client.post("/cash-movements", json=_movimiento())
    assert creado.status_code == 201
    cuerpo = creado.json()
    assert cuerpo["caja"] == "chica" and cuerpo["tipo"] == "ingreso" and cuerpo["monto"] == 500.0
    assert cuerpo["registrado_por"] is not None

    saldo = client.get("/cash-movements/balance").json()
    assert saldo == {"chica": 500.0, "grande": 0.0}


def test_un_egreso_resta_del_saldo(client):
    _como("tesorero")
    client.post("/cash-movements", json=_movimiento(tipo="ingreso", monto=1000))
    client.post("/cash-movements", json=_movimiento(tipo="egreso", monto=300, motivo="Compra de material de limpieza"))

    saldo = client.get("/cash-movements/balance").json()
    assert saldo["chica"] == 700.0


def test_las_dos_cajas_son_independientes(client):
    _como("tesorero")
    client.post("/cash-movements", json=_movimiento(caja="chica", monto=500))
    client.post("/cash-movements", json=_movimiento(caja="grande", monto=20000))
    client.post("/cash-movements", json=_movimiento(caja="grande", tipo="egreso", monto=5000, motivo="Pago a proveedor"))

    saldo = client.get("/cash-movements/balance").json()
    assert saldo == {"chica": 500.0, "grande": 15000.0}


def test_solo_tesoreria_registra_movimientos(client):
    for rol in ("admin", "comite_aprobador", "residente", "guardia"):
        _como(rol)
        assert client.post("/cash-movements", json=_movimiento()).status_code == 403, rol


def test_cualquier_rol_autenticado_ve_el_saldo_y_el_historial(client):
    _como("tesorero")
    client.post("/cash-movements", json=_movimiento())

    for rol in ("admin", "comite_lectura", "residente", "guardia"):
        _como(rol)
        assert client.get("/cash-movements/balance").status_code == 200, rol
        assert len(client.get("/cash-movements").json()) == 1, rol


def test_la_lista_se_puede_filtrar_por_caja_y_fecha(client):
    _como("tesorero")
    client.post("/cash-movements", json=_movimiento(caja="chica", fecha="2026-09-05"))
    client.post("/cash-movements", json=_movimiento(caja="grande", fecha="2026-09-10"))

    solo_chica = client.get("/cash-movements", params={"caja": "chica"}).json()
    assert len(solo_chica) == 1 and solo_chica[0]["caja"] == "chica"

    desde_el_8 = client.get("/cash-movements", params={"desde": "2026-09-08"}).json()
    assert len(desde_el_8) == 1 and desde_el_8[0]["caja"] == "grande"


def test_rechaza_monto_no_positivo_y_motivo_vacio(client):
    _como("tesorero")
    assert client.post("/cash-movements", json=_movimiento(monto=0)).status_code == 422
    assert client.post("/cash-movements", json=_movimiento(monto=-50)).status_code == 422
    assert client.post("/cash-movements", json=_movimiento(motivo="")).status_code == 422


def test_sin_movimientos_el_saldo_es_cero(client):
    _como("tesorero")
    assert client.get("/cash-movements/balance").json() == {"chica": 0.0, "grande": 0.0}
