"""
Revisión: provisioning.py (crea un tenant nuevo) solo importaba 6 módulos de
modelos de tenant, congelado desde la época de F1-07 — TenantBase.metadata
.create_all() en provision_tenant() SOLO crea las tablas de los módulos que
hayan sido importados antes de llamarlo (SQLAlchemy no "descubre" modelos
por sí solo). Cualquier tenant aprovisionado con este script se quedaba sin
budget, expense, announcement, incident, poll, amenity, access_log,
package, visitor_qr, vehicle, lost_found_item y reservation — "relation ...
does not exist" al primer uso de esos módulos. Se encontró al construir
F1-22 (gastos y presupuesto) y probarlo contra un tenant real aprovisionado
en esta sesión.

No se puede probar provision_tenant() de punta a punta contra la suite:
usa CREATE SCHEMA, que no existe en SQLite (la base de las pruebas). Y no
alcanza con inspeccionar TenantBase.metadata en un test normal de pytest:
para cuando cualquier test corre, ya se importó app.main (con todos los
routers, que a su vez importan todos los modelos), así que la metadata
compartida siempre estaría completa sin importar si provisioning.py hace
bien su trabajo — sería una prueba que nunca puede fallar.

En cambio, esta prueba compara directamente el import de provisioning.py
contra los archivos reales en app/models/ que son TenantBase (no
ControlBase) — así si alguien agrega un modelo de tenant nuevo y se le
olvida sumarlo a provisioning.py, esta prueba lo detecta sin depender de
en qué orden se hayan importado los módulos.
"""

import ast
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "app" / "models"
PROVISIONING_FILE = Path(__file__).parent.parent / "app" / "core" / "provisioning.py"

# Modelos de app/models/ que viven en ControlBase (schema público, no por
# tenant) — provisioning.py ya los importa aparte, no deben exigirse aquí.
MODULOS_DE_CONTROL = {"clabe_change_log", "tenant", "tenant_payment", "user_lookup", "vivecom_staff", "__init__"}


def _modulos_de_tenant_en_disco() -> set[str]:
    return {
        archivo.stem
        for archivo in MODELS_DIR.glob("*.py")
        if archivo.stem not in MODULOS_DE_CONTROL
    }


def _modulos_importados_de_app_models(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text())
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module == "app.models":
            modulos.update(alias.name for alias in nodo.names)
    return modulos


def test_provisioning_importa_todos_los_modelos_de_tenant():
    esperados = _modulos_de_tenant_en_disco()
    importados = _modulos_importados_de_app_models(PROVISIONING_FILE)
    faltantes = esperados - importados
    assert not faltantes, (
        f"provisioning.py no importa el/los modelo(s) de tenant: {sorted(faltantes)} — "
        "un tenant nuevo se quedaría sin esas tablas (create_all() no las crea)."
    )
