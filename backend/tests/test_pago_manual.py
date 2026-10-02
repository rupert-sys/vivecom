"""
Pago capturado a mano por el tesorero (efectivo). El alcance decía "no hay pago
en efectivo", pero el reglamento del Condominio Arequipa (Art. 9 IV) lo acepta:
"el pago en efectivo se recibirá en días y horarios a notificar por parte de la
tesorería" y exige entregar recibo (Art. 7 VI).
"""

import uuid

from app.api.deps import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def _como(rol: str, property_id: str | None = None):
    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(
            user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=property_id
        )

    app.dependency_overrides[get_current_user] = override


def _condominio_con_un_cargo(client, monto=750.0):
    prop = client.post("/properties", json={"identificador": "Casa 1"}).json()
    _como("tesorero")  # F0-12: cuotas y cargos son de tesorería, no del administrador
    client.post("/fees", json={"monto": monto, "periodicidad": "mensual", "activa_desde": "2026-01-01"})
    client.post("/fees/generate-charges", params={"periodo": "2026-09-01"})
    return prop


def test_un_condominio_sin_efectivo_activado_rechaza_el_pago_en_efectivo(client):
    prop = _condominio_con_un_cargo(client)
    response = client.post("/payments/manual", json={"property_id": prop["id"], "monto": 750, "metodo": "efectivo"})
    assert response.status_code == 409
    assert "efectivo" in response.json()["detail"]


def test_el_tesorero_registra_un_pago_en_efectivo_y_salda_el_cargo(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    prop = _condominio_con_un_cargo(client, monto=750.0)

    response = client.post("/payments/manual", json={"property_id": prop["id"], "monto": 750, "metodo": "efectivo"})
    assert response.status_code == 201
    pago = response.json()
    assert pago["estado"] == "confirmado"
    assert pago["proveedor"] == "efectivo"
    assert pago["registrado_por"] is not None

    estado = client.get(f"/properties/{prop['id']}/statement").json()
    assert estado["deuda_total"] == 0.0
    assert estado["cargos"][0]["estado"] == "pagado"


def test_un_pago_en_efectivo_de_mas_queda_como_saldo_a_favor(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    prop = _condominio_con_un_cargo(client, monto=750.0)

    client.post("/payments/manual", json={"property_id": prop["id"], "monto": 1000, "metodo": "efectivo"})
    assert client.get(f"/properties/{prop['id']}").json()["saldo_a_favor"] == 250.0


def test_el_recibo_de_un_pago_en_efectivo_se_descarga(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    prop = _condominio_con_un_cargo(client)
    pago = client.post("/payments/manual", json={"property_id": prop["id"], "monto": 750}).json()

    recibo = client.get(f"/payments/{pago['id']}/receipt")
    assert recibo.status_code == 200
    assert recibo.headers["content-type"] == "application/pdf"


def test_una_transferencia_manual_no_requiere_que_el_efectivo_este_activado(client):
    prop = _condominio_con_un_cargo(client)
    response = client.post(
        "/payments/manual", json={"property_id": prop["id"], "monto": 750, "metodo": "transferencia"}
    )
    assert response.status_code == 201


def test_solo_tesorero_o_admin_registran_pagos_manuales(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    prop = _condominio_con_un_cargo(client)
    for rol in ("residente", "guardia", "comite_lectura"):
        _como(rol, property_id=prop["id"])
        assert client.post("/payments/manual", json={"property_id": prop["id"], "monto": 750}).status_code == 403
    _como("tesorero")
    assert client.post("/payments/manual", json={"property_id": prop["id"], "monto": 750}).status_code == 201


def test_rechaza_monto_no_positivo_y_vivienda_inexistente(client):
    client.patch("/tenant/reglamento", json={"acepta_pago_efectivo": True})
    prop = _condominio_con_un_cargo(client)
    assert client.post("/payments/manual", json={"property_id": prop["id"], "monto": 0}).status_code == 422
    assert client.post("/payments/manual", json={"property_id": str(uuid.uuid4()), "monto": 5}).status_code == 404
