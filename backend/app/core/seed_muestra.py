"""
Siembra un condominio de MUESTRA para que las personas de una demostración entren desde el primer momento:
un condominio inventado con el reglamento de Arequipa, 10 usuarios (administración, tesorería, comité y siete
residentes con su vivienda), tres meses de cuotas, cuatro viviendas al corriente y tres con adeudo (para probar el
acuerdo de pago y los comprobantes), un aviso con dudas, una votación y un área común.

Todo es inventado y editable desde el panel (Usuarios, Viviendas, Reglamento). Las contraseñas se generan al azar y
se guardan en un archivo Markdown (no se suben al repositorio: deploy/credenciales-muestra.md).

Corre por HTTP contra un backend levantado:

    python -m app.core.seed_muestra --api http://127.0.0.1:8010 --salida ../deploy/credenciales-muestra.md

Se puede correr UNA vez por correo de administrador: si ya existe, se detiene sin tocar nada.
"""

import argparse
import secrets
import string
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

TZ = ZoneInfo("America/Mexico_City")
DOMINIO_CORREOS = "muestra.vivecom.com.mx"  # los correos no reciben nada: solo sirven para iniciar sesión
CONDOMINIO = "Residencial Las Jacarandas (muestra)"
CLABE = "646180157012345678"
CUOTA = 750.0

RESIDENTES = [  # (vivienda, persona, situación)
    ("Casa 1", "Mariana Ortega Salazar", "al corriente"),
    ("Casa 2", "Luis Fernando Peña Ruiz", "al corriente"),
    ("Casa 3", "Carmen Beltrán Aguilar", "al corriente"),
    ("Casa 4", "Jorge Ramírez Cota", "al corriente"),
    ("Casa 5", "Ana Lucía Duarte Mora", "con adeudo (prueba: acuerdo de pago y comprobante)"),
    ("Casa 6", "Roberto Villaseñor Lara", "con adeudo (prueba: acuerdo de pago y comprobante)"),
    ("Casa 7", "Sofía Navarro Ibarra", "con adeudo (prueba: acuerdo de pago y comprobante)"),
]
PERSONAL = [  # (rol, persona, correo)
    ("admin", "Administración Las Jacarandas", "administracion"),
    ("tesorero", "Patricia Gómez Ledesma (Tesorería)", "tesoreria"),
    ("comite_aprobador", "Héctor Salas Ponce (Comité)", "comite"),
]


def _clave() -> str:
    alfabeto = string.ascii_letters.replace("l", "").replace("I", "").replace("O", "") + "23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(10))


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _primer_dia(hoy: date, meses_atras: int) -> date:
    total = hoy.year * 12 + (hoy.month - 1) - meses_atras
    return date(total // 12, total % 12 + 1, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://127.0.0.1:8010")
    parser.add_argument("--salida", default="credenciales-muestra.md")
    args = parser.parse_args()
    hoy = datetime.now(TZ).date()

    correo_admin = f"administracion@{DOMINIO_CORREOS}"
    claves = {correo_admin: _clave()}

    with httpx.Client(base_url=args.api, timeout=90.0) as c:
        def ok(r: httpx.Response, que: str) -> httpx.Response:
            if r.status_code >= 400:
                raise SystemExit(f"✗ {que}: {r.status_code} {r.text[:200]}")
            return r

        ya = c.post("/auth/login", json={"email": correo_admin, "password": "x"})
        if ya.status_code != 401 and ya.status_code != 422:
            print(f"Respuesta inesperada al comprobar si ya existe ({ya.status_code}); se detiene.", file=sys.stderr)
            return 1
        registro = c.post("/signup", json={"nombre_condominio": CONDOMINIO, "admin_email": correo_admin,
                                           "admin_password": claves[correo_admin], "clabe_destino": CLABE})
        if registro.status_code == 409:
            print(f"Ya existe una cuenta {correo_admin}: la muestra ya estaba sembrada. No se tocó nada.", file=sys.stderr)
            return 1
        ok(registro, "registro del condominio")
        admin = ok(c.post("/auth/login", json={"email": correo_admin, "password": claves[correo_admin]}), "login admin").json()["access_token"]
        A = _h(admin)

        # Reglamento de Arequipa (mismo que el recorrido de punta a punta)
        ok(c.patch("/tenant/reglamento", headers=A, json={
            "dia_limite_pago": 5, "recargo_porcentaje": 0.05, "recargo_modalidad": "mensual_sobre_saldo",
            "acepta_pago_efectivo": True, "morosos_sin_voto": True, "morosos_sin_areas_comunes": True,
            "gasto_umbral_asamblea": 10000, "cotizaciones_minimas": 3, "cajones_visitas": 7,
            "horas_max_estacionamiento_visitas": 24, "dudas_en_avisos_por_defecto": False,
        }), "reglamento")
        ok(c.post("/fees", headers=A, json={"monto": CUOTA, "periodicidad": "mensual", "activa_desde": "2026-01-01"}), "cuota")

        # Viviendas, personas y cuentas
        casas = {}
        for vivienda, persona, _ in RESIDENTES:
            casas[vivienda] = ok(c.post("/properties", headers=A, json={"identificador": vivienda}), f"vivienda {vivienda}").json()
        cuentas = []  # (rol, persona, vivienda, correo, clave)
        for rol, persona, alias in PERSONAL:
            correo = correo_admin if rol == "admin" else f"{alias}@{DOMINIO_CORREOS}"
            if rol != "admin":
                claves[correo] = _clave()
                ok(c.post("/users", headers=A, json={"email": correo, "password": claves[correo], "rol": rol}), f"cuenta {rol}")
            cuentas.append((rol, persona, "—", correo, claves[correo]))
        ids = {u["email"]: u["id"] for u in ok(c.get("/users", headers=A), "lista de cuentas").json()}
        for n, (vivienda, persona, _) in enumerate(RESIDENTES, start=1):
            correo = f"casa{n}@{DOMINIO_CORREOS}"
            claves[correo] = _clave()
            ok(c.post("/users", headers=A, json={"email": correo, "password": claves[correo], "rol": "residente",
                                                 "property_id": casas[vivienda]["id"]}), f"cuenta {vivienda}")
            persona_id = ok(c.post("/residents", headers=A, json={"nombre": persona, "telefono": f"+52 55 5550 01{n:02d}"}),
                            f"residente {persona}").json()["id"]
            ok(c.post(f"/properties/{casas[vivienda]['id']}/residents", headers=A,
                      json={"resident_id": persona_id, "rol": "propietario"}), f"vincular {persona}")
            cuentas.append(("residente", persona, vivienda, correo, claves[correo]))

        def login(correo: str) -> str:
            return ok(c.post("/auth/login", json={"email": correo, "password": claves[correo]}), f"login {correo}").json()["access_token"]

        T = _h(login(f"tesoreria@{DOMINIO_CORREOS}"))

        # Tres meses de cuotas; cuatro viviendas pagan (efectivo) antes de que corra el recargo, tres quedan debiendo
        for meses in (2, 1, 0):
            ok(c.post("/fees/generate-charges", headers=A, params={"periodo": _primer_dia(hoy, meses).isoformat()}), "cargos")
        for vivienda, _, situacion in RESIDENTES:
            if situacion == "al corriente":
                deuda = ok(c.get(f"/properties/{casas[vivienda]['id']}/statement", headers=A), f"estado {vivienda}").json()["deuda_total"]
                ok(c.post("/payments/manual", headers=T, json={"property_id": casas[vivienda]["id"], "monto": deuda, "metodo": "efectivo"}),
                   f"pago {vivienda}")
        ok(c.post("/fees/apply-late-surcharges", headers=A), "recargos")

        # Un área común, un aviso con dudas y una votación abierta
        area = ok(c.post("/amenities", headers=A, json={
            "nombre": "Área adoquinada", "periodo_limite_horas": 48, "dias_anticipacion_minimos": 8, "hora_fin_maxima": "01:00",
            "cuota": 1000, "notas_reglamento": "Reglamento Art. 2 III-VIII"}), "área común").json()
        ok(c.post(f"/amenities/{area['id']}/approvers", headers=A,
                  json={"user_id": ids[f"comite@{DOMINIO_CORREOS}"]}), "aprobador del área")
        ok(c.post("/announcements", headers=A, json={
            "titulo": "Bienvenidos a la muestra de Vivecom", "permite_dudas": True,
            "contenido": "Esta es una demostración con datos inventados. Pueden revisar su estado de cuenta, mandar un "
                         "comprobante, pedir un acuerdo de pago, reservar el área adoquinada y escribir una duda aquí mismo."}), "aviso")
        ok(c.post("/polls", headers=A, json={
            "pregunta": "¿Cambiamos el portón de acceso?", "opciones": ["Sí", "No"],
            "fecha_cierre": (hoy + timedelta(days=30)).isoformat()}), "votación")

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# Muestra de Vivecom — {CONDOMINIO}", "",
        f"Generado el {hoy.isoformat()}. **Todo es inventado y editable** desde el panel (Usuarios, Viviendas, Reglamento).",
        "No se sube al repositorio. Las contraseñas no se pueden recuperar: cámbialas desde Usuarios → Editar.", "",
        "- Panel de administración: https://panel.vivecom.com.mx (administración, tesorería y comité)",
        "- App web para iPhone: https://app.vivecom.com.mx (Safari → Compartir → Añadir a pantalla de inicio)",
        "- App para Android: el APK que se comparte aparte", "",
        "| Persona | Rol | Vivienda | Correo | Contraseña |", "|---|---|---|---|---|",
    ]
    for rol, persona, vivienda, correo, clave in cuentas:
        lineas.append(f"| {persona} | {rol} | {vivienda} | `{correo}` | `{clave}` |")
    lineas += ["", "Situación de las viviendas: " + "; ".join(f"{v}: {s}" for v, _, s in RESIDENTES) + "."]
    salida.write_text("\n".join(lineas) + "\n")
    salida.chmod(0o600)
    print(f"✓ Muestra sembrada: {len(cuentas)} usuarios. Credenciales en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
