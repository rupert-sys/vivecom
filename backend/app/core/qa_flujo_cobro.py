"""
F1-29: QA de punta a punta del flujo de cobro completo — transferencia,
detección, conciliación, pago anticipado, saldo a favor y rechazo.

No se puede correr contra la suite de pytest con SQLite: /signup y
/auth/login usan control_session()/tenant_session() directamente (mismo
límite documentado en test_signup.py y test_users.py), y el webhook de STP
necesita una firma HMAC real más un tenant real con su propio schema de
Postgres. Este guion reproduce el escenario completo contra un backend real
(uvicorn + Postgres.app) para poder re-correrlo cuando haga falta, en vez
de dejarlo como comandos sueltos en el historial de una sesión.

Uso (con el backend corriendo en localhost:8000):
    python -m app.core.qa_flujo_cobro

Cada corrida crea un tenant y una CLABE nuevos (sufijo aleatorio) — el
dinero se acumula dentro de una corrida (depósitos, saldo a favor), así
que el guion NO es idempotente contra el MISMO tenant; en vez de intentar
reutilizar uno existente, cada ejecución parte de cero para que las
aserciones sobre el estado final sean siempre válidas.

Para dejar sembrado el estado que espera la prueba de integración del
lado de Flutter (mobile/test/integration/real_backend_test.dart, tag
"integration"), correr con --fijo: usa el tenant/residente/CLABE fijos
que esa prueba tiene hardcodeados.
"""

import argparse
import hashlib
import hmac
import json
import secrets
import sys

import httpx

BASE_URL = "http://localhost:8000"
STP_WEBHOOK_SECRET = "cambia-esto-en-produccion"  # noqa: S105 — valor de desarrollo, no un secreto real


def _firmar(body: dict) -> tuple[bytes, str]:
    raw = json.dumps(body).encode()
    firma = hmac.new(STP_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, firma


def _depositar(client: httpx.Client, *, clabe: str, monto: str, referencia: str, clave_rastreo: str) -> dict:
    body = {
        "monto": monto,
        "referenciaNumerica": referencia,
        "claveRastreo": clave_rastreo,
        "fechaOperacion": "2026-09-16T12:00:00",
        "cuentaBeneficiario": clabe,
    }
    raw, firma = _firmar(body)
    response = client.post(
        "/payments/webhook/stp", content=raw, headers={"X-STP-Signature": firma, "Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json()


def main(fijo: bool) -> None:
    sufijo = "" if fijo else str(secrets.randbelow(900000) + 100000)
    admin_email = f"admin{sufijo}@qaflujof129.mx" if sufijo else "admin@qaflujof129.mx"
    admin_password = "AdminQA12345"
    residente_email = f"residente{sufijo}@qaflujof129.mx" if sufijo else "residente2@qaflujof129.mx"
    residente_password = "ResidenteQA123"
    # 18 dígitos numéricos exactos (la CLABE no admite letras) — se arma con
    # el sufijo aleatorio para que corridas distintas no choquen entre sí.
    clabe = (sufijo or "99991").rjust(18, "9")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        print(f"1. Aprovisionando tenant (CLABE {clabe}) vía /signup...")
        signup = client.post(
            "/signup",
            json={
                "nombre_condominio": "QA Flujo de Cobro F1-29",
                "admin_email": admin_email,
                "admin_password": admin_password,
                "clabe_destino": clabe,
            },
        )
        if fijo and signup.status_code == 409:
            print("   (el tenant ya existía de una corrida anterior con --fijo, se reutiliza)")
        else:
            signup.raise_for_status()

        admin_token = client.post(
            "/auth/login", json={"email": admin_email, "password": admin_password}
        ).json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        print("2. Creando vivienda y residente...")
        prop = client.post("/properties", json={"identificador": "Casa QA-1"}, headers=admin_headers).json()
        prop_id = prop["id"]

        user_resp = client.post(
            "/users",
            json={"email": residente_email, "password": residente_password, "rol": "residente", "property_id": prop_id},
            headers=admin_headers,
        )
        if fijo and user_resp.status_code == 409:
            print("   (el residente ya existía de una corrida anterior con --fijo, se reutiliza)")
        else:
            user_resp.raise_for_status()
            assert user_resp.json()["property_id"] == prop_id, "el residente debe quedar asociado a la vivienda"

        client.post(
            "/fees", json={"monto": 1000.00, "periodicidad": "mensual", "activa_desde": "2026-01-01"},
            headers=admin_headers,
        )
        client.post("/fees/generate-charges", headers=admin_headers)

        residente_token = client.post(
            "/auth/login", json={"email": residente_email, "password": residente_password}
        ).json()["access_token"]
        residente_headers = {"Authorization": f"Bearer {residente_token}"}

        print("3. Residente ve su cargo pendiente...")
        estado = client.get(f"/properties/{prop_id}/statement", headers=residente_headers).json()
        assert estado["deuda_total"] == 1000.0, estado

        print("4. Depósito exacto → conciliación automática...")
        _depositar(client, clabe=clabe, monto="1000.00", referencia="0000001", clave_rastreo=f"STP-QA{sufijo}-001")
        estado = client.get(f"/properties/{prop_id}/statement", headers=residente_headers).json()
        assert estado["deuda_total"] == 0.0
        assert estado["cargos"][0]["estado"] == "pagado"

        print("5. Depósito exacto sin deuda pendiente → pago anticipado (F1-08)...")
        _depositar(
            client, clabe=clabe, monto="1000.00", referencia="0000001", clave_rastreo=f"STP-QA{sufijo}-ANTICIPADO"
        )
        estado = client.get(f"/properties/{prop_id}/statement", headers=residente_headers).json()
        assert len(estado["cargos"]) == 2, "debió crearse el cargo del mes siguiente, ya pagado"
        assert all(c["estado"] == "pagado" for c in estado["cargos"])

        print("6. Depósito no múltiplo exacto → saldo a favor (F1-09)...")
        _depositar(
            client, clabe=clabe, monto="350.00", referencia="0000001", clave_rastreo=f"STP-QA{sufijo}-SALDOFAVOR"
        )
        propiedad = client.get(f"/properties/{prop_id}", headers=residente_headers).json()
        assert propiedad["saldo_a_favor"] == 350.0

        print("7. Depósito sin referencia reconocida → pendiente → tesorero rechaza...")
        sin_match = _depositar(
            client, clabe=clabe, monto="500.00", referencia="9999999", clave_rastreo=f"STP-QA{sufijo}-SINMATCH"
        )
        assert sin_match["payment_estado"] == "pendiente"
        rechazo = client.post(f"/payments/{sin_match['payment_id']}/reject", headers=admin_headers)
        rechazo.raise_for_status()
        assert rechazo.json()["estado"] == "rechazado"

        print("\nTodo el flujo de cobro se validó de punta a punta contra Postgres real.")
        print(f"Estado final de {prop['identificador']}: {json.dumps(estado, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fijo",
        action="store_true",
        help="usa las credenciales fijas que espera real_backend_test.dart en vez de un sufijo aleatorio",
    )
    args = parser.parse_args()

    try:
        main(fijo=args.fijo)
    except AssertionError as exc:
        print(f"FALLÓ: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"FALLÓ: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        sys.exit(1)
