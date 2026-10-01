"""
Siembra San Miguel (muestra) — el condominio de demostración de 30 viviendas ya creado desde el portal de
administrador principal (admin.vivecom.com.mx) — con residentes inventados, cuota mensual de $750 y una mezcla
realista de propietarios/inquilinos y de viviendas al corriente/morosas. Mismo patrón que seed_muestra.py, pero
activa las 30 cuentas de vivienda que /signup ya dejó sin activar en vez de crear un condominio desde cero.

Corre por HTTP contra el backend público:

    python -m app.core.seed_san_miguel --api https://api.vivecom.com.mx --salida ../deploy/credenciales-san-miguel.md

Se detiene sin tocar nada si la cuenta del admin ya cambió su password temporal (señal de que ya se sembró).
"""

import argparse
import secrets
import string
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

TZ = ZoneInfo("America/Mexico_City")
CONDOMINIO = "San Miguel (muestra)"
DOMINIO = "sanmiguelmuestra.com.mx"
CUOTA = 750.0
CANTIDAD_CASAS = 30
# Las últimas 8 (de 30) quedan morosas — proporción realista (~27%) para poder mostrar acuerdos de pago,
# comprobantes y recargos en la demo. El resto queda al corriente.
CASAS_MOROSAS = {23, 24, 25, 26, 27, 28, 29, 30}

NOMBRES = [
    "María Fernanda López Hidalgo", "José Luis Martínez Cano", "Guadalupe Reyes Montoya",
    "Ricardo Alan Torres Nieto", "Alejandra Paz Cervantes", "Francisco Javier Domínguez Lara",
    "Verónica Isabel Chávez Rosales", "Miguel Ángel Sandoval Vega", "Diana Laura Esquivel Rangel",
    "Sergio Iván Contreras Meza", "Karla Patricia Bautista Solís", "Eduardo Daniel Marín Cortés",
    "Rosa Elena Gutiérrez Padilla", "Óscar Emmanuel Vázquez Rivas", "Claudia Beatriz Ojeda Fuentes",
    "Héctor Iván Salgado Núñez", "Brenda Carolina Zúñiga Ibáñez", "Adrián Gerardo Palacios Cuevas",
    "Leticia Guadalupe Herrera Campos", "Fernando Josué Aranda Delgado", "Paola Ximena Barrera Guzmán",
    "Raúl Alejandro Cordero Soto", "Mónica Alejandra Villagómez Pérez", "Jorge Iván Becerra Aguirre",
    "Silvia Renata Cabrera Ponce", "Iván Alexis Rentería Mora", "Andrea Michelle Escobedo Vidal",
    "Luis Fernando Quintero Salas", "Gabriela Itzel Manríquez Osorio", "Daniel Ernesto Villanueva Prado",
]
# (casa 1-indexada) -> rol de ocupación. 1 de cada 3 aprox. es inquilino, el resto propietario.
INQUILINOS = {3, 6, 9, 12, 15, 18, 21, 24, 27, 30}


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
    parser.add_argument("--api", default="https://api.vivecom.com.mx")
    parser.add_argument("--salida", default="credenciales-san-miguel.md")
    args = parser.parse_args()
    hoy = datetime.now(TZ).date()

    correo_admin = f"administracion@{DOMINIO}"
    claves = {correo_admin: CONDOMINIO}  # contraseña inicial de /signup: el propio nombre del condominio

    with httpx.Client(base_url=args.api, timeout=90.0) as c:
        def ok(r: httpx.Response, que: str) -> httpx.Response:
            if r.status_code >= 400:
                raise SystemExit(f"✗ {que}: {r.status_code} {r.text[:300]}")
            return r

        login = ok(c.post("/auth/login", json={"email": correo_admin, "password": claves[correo_admin]}), "login admin")
        payload = login.json()
        admin_token = payload["access_token"]
        A = _h(admin_token)

        ok(c.post("/fees", headers=A, json={"monto": CUOTA, "periodicidad": "mensual", "activa_desde": "2026-01-01"}), "cuota")
        # Sin esto, /payments/manual rechaza cualquier pago en efectivo con 409 — encontrado en la corrida real
        # contra producción (2026-09-29): el script llegaba hasta aquí y tronaba en el primer pago.
        ok(c.patch("/tenant/reglamento", headers=A, json={
            "dia_limite_pago": 5, "recargo_porcentaje": 0.05, "recargo_modalidad": "mensual_sobre_saldo",
            "acepta_pago_efectivo": True, "morosos_sin_voto": True, "morosos_sin_areas_comunes": True,
            "gasto_umbral_asamblea": 10000, "cotizaciones_minimas": 3, "cajones_visitas": 7,
            "horas_max_estacionamiento_visitas": 24, "dudas_en_avisos_por_defecto": False,
        }), "reglamento")

        propiedades = {p["identificador"]: p for p in ok(c.get("/properties", headers=A), "listar viviendas").json()}

        cuentas = [("admin", "Administración San Miguel", "—", correo_admin, claves[correo_admin])]
        residentes_por_casa = {}
        for n, nombre in enumerate(NOMBRES, start=1):
            casa = f"Casa {n}"
            rol = "inquilino" if n in INQUILINOS else "propietario"
            clave = _clave()
            correo_casa = f"casa{n}@{DOMINIO}"
            ok(c.post("/residents/activar", json={
                "nombre_condominio": CONDOMINIO, "numero_de_casa": n, "nombre_completo": nombre, "rol": rol,
                "telefono": f"+52 55 5550 {n:04d}"[:16], "password": clave,
            }), f"activar {casa}")
            claves[correo_casa] = clave
            situacion = "con adeudo (moroso, prueba de recargos/acuerdo de pago)" if n in CASAS_MOROSAS else "al corriente"
            cuentas.append(("residente", nombre, casa, correo_casa, clave))
            residentes_por_casa[casa] = (nombre, rol, situacion)

        # Tesorería: una cuenta propia, para registrar los pagos como lo haría tesorería en la vida real.
        correo_tesoreria = f"tesoreria@{DOMINIO}"
        claves[correo_tesoreria] = _clave()
        ok(c.post("/users", headers=A, json={"email": correo_tesoreria, "password": claves[correo_tesoreria], "rol": "tesorero"}),
           "cuenta tesorería")
        cuentas.insert(1, ("tesorero", "Tesorería San Miguel", "—", correo_tesoreria, claves[correo_tesoreria]))
        T = _h(ok(c.post("/auth/login", json={"email": correo_tesoreria, "password": claves[correo_tesoreria]}), "login tesorería").json()["access_token"])

        # Tres meses de cuotas; las viviendas NO morosas pagan en efectivo antes del recargo.
        for meses in (2, 1, 0):
            ok(c.post("/fees/generate-charges", headers=A, params={"periodo": _primer_dia(hoy, meses).isoformat()}), "cargos")
        for casa, propiedad in propiedades.items():
            n = int(casa.split(" ")[1])
            if n not in CASAS_MOROSAS:
                deuda = ok(c.get(f"/properties/{propiedad['id']}/statement", headers=A), f"estado {casa}").json()["deuda_total"]
                if deuda > 0:
                    ok(c.post("/payments/manual", headers=T, json={"property_id": propiedad["id"], "monto": deuda, "metodo": "efectivo"}),
                       f"pago {casa}")
        ok(c.post("/fees/apply-late-surcharges", headers=A), "recargos")

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# Muestra de Vivecom — {CONDOMINIO}", "",
        f"Generado el {hoy.isoformat()}. **Todo es inventado y editable** desde el panel (Usuarios, Viviendas, Reglamento).",
        "No se sube al repositorio. Las contraseñas no se pueden recuperar: cámbialas desde Usuarios → Editar.", "",
        "- Panel de administración: https://panel.vivecom.com.mx (administración, tesorería y comité)",
        "- App web para iPhone: https://app.vivecom.com.mx (Safari → Compartir → Añadir a pantalla de inicio)", "",
        "| Persona | Rol | Vivienda | Correo | Contraseña |", "|---|---|---|---|---|",
    ]
    for rol, persona, vivienda, correo, clave in cuentas:
        lineas.append(f"| {persona} | {rol} | {vivienda} | `{correo}` | `{clave}` |")
    lineas += [
        "",
        f"{CANTIDAD_CASAS - len(CASAS_MOROSAS)} vivienda(s) al corriente, {len(CASAS_MOROSAS)} morosa(s) "
        f"(Casa {min(CASAS_MOROSAS)} a Casa {max(CASAS_MOROSAS)}) — para probar recargos, acuerdos de pago y comprobantes.",
        f"{len(INQUILINOS)} vivienda(s) con inquilino, {CANTIDAD_CASAS - len(INQUILINOS)} con propietario viviendo ahí.",
    ]
    salida.write_text("\n".join(lineas) + "\n")
    salida.chmod(0o600)
    print(f"✓ San Miguel sembrado: {len(cuentas)} usuarios. Credenciales en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
