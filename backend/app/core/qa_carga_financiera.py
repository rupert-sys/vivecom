"""
F1-37: pruebas de carga del módulo financiero — generación masiva de cargos
y detección de pagos concurrentes, contra un backend real (uvicorn +
Postgres.app), no contra la suite de pytest con SQLite. Mismo motivo que
qa_flujo_cobro.py (F1-29): /signup, /auth/login y el webhook de STP no se
pueden ejercitar contra esa suite.

Qué agrega esto sobre las pruebas de concurrencia que YA existen en pytest
(test_fee_charges.py::test_concurrent_generation_for_same_period_does_not_double_charge,
test_saldo_a_favor.py::test_concurrent_deposits_do_not_lose_credit_updates):
esas corren con 2-3 registros contra SQLite en memoria — útiles para probar
la lógica en sí, pero no dicen nada sobre volumen real ni sobre Postgres
real (tipos de dato, planificador de queries, tiempos de commit distintos a
SQLite — la clase de diferencia que ya causó bugs reales invisibles en
SQLite antes en este proyecto, ver F1-29/F2-19). Este guion sí genera cargos
para decenas/cientos de viviendas y dispara depósitos concurrentes de
verdad vía HTTP contra Postgres, midiendo tiempos.

Lo que esto NO prueba (limitación ya conocida y documentada en el propio
código — ver advertir_si_with_for_update_es_no_op en core/concurrency.py):
el servidor de desarrollo corre como UN solo proceso, así que el candado en
memoria (asyncio.Lock) por vivienda/periodo ya serializa cualquier
concurrencia que este guion pueda generar, ANTES de que el with_for_update()
de Postgres entre en juego — no hay forma de ejercitar la protección
verdaderamente entre-procesos (el motivo real de ese with_for_update) sin
levantar el backend con más de un worker, que está fuera del alcance de un
guion de QA. Lo que SÍ queda validado de punta a punta contra Postgres real
es que, bajo carga y con muchas escrituras concurrentes reales, ningún
depósito se pierde ni se cruza con el de otra vivienda.

Uso (con el backend corriendo en localhost:8000 contra Postgres real):
    python -m app.core.qa_carga_financiera [--propiedades 100]
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import secrets
import sys
import time

import httpx

BASE_URL = "http://localhost:8000"
STP_WEBHOOK_SECRET = "cambia-esto-en-produccion"  # noqa: S105 — valor de desarrollo, no un secreto real


def _firmar(body: dict) -> tuple[bytes, str]:
    raw = json.dumps(body).encode()
    firma = hmac.new(STP_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, firma


async def _depositar(
    client: httpx.AsyncClient, *, clabe: str, monto: str, referencia: str, clave_rastreo: str
) -> dict:
    body = {
        "monto": monto,
        "referenciaNumerica": referencia,
        "claveRastreo": clave_rastreo,
        "fechaOperacion": "2026-09-16T12:00:00",
        "cuentaBeneficiario": clabe,
    }
    raw, firma = _firmar(body)
    response = await client.post(
        "/payments/webhook/stp", content=raw, headers={"X-STP-Signature": firma, "Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json()


async def main(n_propiedades: int) -> None:
    sufijo = str(secrets.randbelow(900000) + 100000)
    admin_email = f"admin{sufijo}@qacargaf137.mx"
    admin_password = "AdminQA12345"
    clabe = sufijo.rjust(18, "9")
    monto_cuota = 1000.00

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        print(f"1. Aprovisionando tenant (CLABE {clabe}) vía /signup...")
        signup = await client.post(
            "/signup",
            json={
                "nombre_condominio": "QA Carga Financiera F1-37",
                "admin_email": admin_email,
                "admin_password": admin_password,
                "clabe_destino": clabe,
            },
        )
        signup.raise_for_status()

        login = await client.post("/auth/login", json={"email": admin_email, "password": admin_password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        print(f"2. Creando {n_propiedades} viviendas...")
        t0 = time.perf_counter()
        propiedades = []
        for i in range(1, n_propiedades + 1):
            resp = await client.post("/properties", json={"identificador": f"Casa {i}"}, headers=headers)
            resp.raise_for_status()
            propiedades.append(resp.json())
        t_creacion = time.perf_counter() - t0
        print(f"   {n_propiedades} viviendas creadas en {t_creacion:.2f}s")

        await client.post(
            "/fees", json={"monto": monto_cuota, "periodicidad": "mensual", "activa_desde": "2026-01-01"},
            headers=headers,
        )

        print("3. Generación masiva de cargos (un disparo para todas las viviendas)...")
        t0 = time.perf_counter()
        gen = await client.post("/fees/generate-charges", headers=headers)
        gen.raise_for_status()
        t_generacion = time.perf_counter() - t0
        cargos_generados = gen.json()["cargos_generados"]
        print(f"   {cargos_generados} cargos generados en {t_generacion:.3f}s")
        assert cargos_generados == n_propiedades, f"se esperaban {n_propiedades} cargos, se generaron {cargos_generados}"

        print("4. Disparo concurrente del mismo periodo (job de Celery + trigger manual compitiendo)...")
        resultados_gen = await asyncio.gather(
            client.post("/fees/generate-charges", headers=headers),
            client.post("/fees/generate-charges", headers=headers),
        )
        for r in resultados_gen:
            r.raise_for_status()
        extra = sum(r.json()["cargos_generados"] for r in resultados_gen)
        assert extra == 0, f"generar dos veces más para el mismo periodo NO debe duplicar cargos, se generaron {extra} de más"
        print("   sin duplicados: dos disparos más para el mismo periodo generaron 0 cargos extra")

        print(f"5. {n_propiedades} depósitos concurrentes (uno por vivienda, importe exacto de la cuota)...")
        t0 = time.perf_counter()
        tareas = [
            _depositar(
                client, clabe=clabe, monto=f"{monto_cuota:.2f}", referencia=prop["referencia_pago"],
                clave_rastreo=f"STP-QA{sufijo}-{prop['id']}",
            )
            for prop in propiedades
        ]
        resultados_depositos = await asyncio.gather(*tareas)
        t_depositos = time.perf_counter() - t0
        print(f"   {len(resultados_depositos)} depósitos concurrentes procesados en {t_depositos:.2f}s")
        no_confirmados = [r for r in resultados_depositos if r.get("payment_estado") != "confirmado"]
        assert not no_confirmados, (
            f"todos los depósitos con referencia exacta debían confirmarse, {len(no_confirmados)} no lo hicieron: "
            f"{no_confirmados[:3]}"
        )

        print("6. Verificando que cada vivienda quedó en $0 de deuda, sin cruces con otra vivienda...")
        for prop in propiedades:
            estado = (await client.get(f"/properties/{prop['id']}/statement", headers=headers)).json()
            assert estado["deuda_total"] == 0.0, f"{prop['identificador']} debería tener deuda 0, tiene {estado['deuda_total']}"
        print(f"   {n_propiedades} viviendas verificadas en $0 de deuda — ningún depósito se cruzó con otra vivienda")

        print("7. Dos depósitos concurrentes más a la MISMA vivienda (pago anticipado, F1-08)...")
        prop_prueba = propiedades[0]
        t0 = time.perf_counter()
        dep_a, dep_b = await asyncio.gather(
            _depositar(
                client, clabe=clabe, monto=f"{monto_cuota:.2f}", referencia=prop_prueba["referencia_pago"],
                clave_rastreo=f"STP-QA{sufijo}-RACE-A",
            ),
            _depositar(
                client, clabe=clabe, monto=f"{monto_cuota:.2f}", referencia=prop_prueba["referencia_pago"],
                clave_rastreo=f"STP-QA{sufijo}-RACE-B",
            ),
        )
        t_race = time.perf_counter() - t0
        assert dep_a["payment_estado"] == "confirmado" and dep_b["payment_estado"] == "confirmado"
        estado_final = (await client.get(f"/properties/{prop_prueba['id']}/statement", headers=headers)).json()
        cargos_pagados = sum(1 for c in estado_final["cargos"] if c["estado"] == "pagado")
        print(f"   dos depósitos concurrentes de ${monto_cuota:.2f} resueltos en {t_race:.3f}s, {cargos_pagados} cargos pagados en total")
        assert cargos_pagados == 3, (
            f"se esperaban 3 cargos pagados (el original del paso 5 + 2 meses anticipados de la carrera), hay "
            f"{cargos_pagados} — indicaría que uno de los dos depósitos concurrentes se perdió (lost update) o "
            "que ambos reclamaron el mismo mes futuro"
        )

        print("\nResumen de carga:")
        print(f"  - Creación de {n_propiedades} viviendas: {t_creacion:.2f}s ({n_propiedades / t_creacion:.1f} req/s)")
        print(f"  - Generación de {cargos_generados} cargos en un solo disparo: {t_generacion:.3f}s")
        print(f"  - {n_propiedades} depósitos concurrentes: {t_depositos:.2f}s ({n_propiedades / t_depositos:.1f} req/s)")
        print(f"  - 2 depósitos concurrentes a la misma vivienda: {t_race:.3f}s, sin lost update")
        print("\nMódulo financiero validado bajo carga contra Postgres real.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--propiedades", type=int, default=100,
        help="número de viviendas a simular (default: 100 — el piso documentado en el alcance es 50)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.propiedades))
    except AssertionError as exc:
        print(f"FALLÓ: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"FALLÓ: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        sys.exit(1)
