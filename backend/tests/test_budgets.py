"""
F1-16 / HU-A10: presupuesto por categoría (mensual por defecto, o anual) y
el reporte que lo compara contra el gasto real.
F0-12: solo tesorería crea presupuestos (antes era el administrador).
"""


def _como(rol: str) -> None:
    import uuid

    from app.api.deps import get_current_user
    from app.main import app
    from app.schemas.auth import CurrentUser

    tenant_id = app.dependency_overrides[get_current_user]().tenant_id

    def override():
        return CurrentUser(user_id=str(uuid.uuid4()), tenant_id=tenant_id, schema_name="test", rol=rol, property_id=None)

    app.dependency_overrides[get_current_user] = override


def _gasto(client, categoria, monto, fecha):
    client.post(
        "/expenses",
        json={"categoria": categoria, "monto": monto, "comprobante_url": "https://x/c.pdf", "fecha": fecha},
    )


def test_create_and_list_budget(client):
    _como("tesorero")
    created = client.post(
        "/budgets",
        json={"categoria": "Mantenimiento", "periodicidad": "mensual", "periodo": "2026-09-01", "monto_planeado": 5000.00},
    )
    assert created.status_code == 201

    listado = client.get("/budgets").json()
    assert len(listado) == 1
    assert listado[0]["categoria"] == "Mantenimiento"


def test_solo_tesoreria_crea_presupuestos(client):
    """F0-12: el administrador ya no puede crear presupuestos (antes sí podía) — solo tesorería."""
    for rol in ("admin", "comite_aprobador", "residente", "guardia"):
        _como(rol)
        response = client.post(
            "/budgets",
            json={"categoria": "Mantenimiento", "periodicidad": "mensual", "periodo": "2026-09-01", "monto_planeado": 5000.00},
        )
        assert response.status_code == 403, rol


def test_report_compares_monthly_budget_against_actual_expenses(client):
    _como("tesorero")
    client.post(
        "/budgets",
        json={"categoria": "Mantenimiento", "periodicidad": "mensual", "periodo": "2026-09-01", "monto_planeado": 5000.00},
    )
    _gasto(client, "Mantenimiento", 1200.00, "2026-09-05")
    _gasto(client, "Mantenimiento", 800.00, "2026-09-20")
    _gasto(client, "Mantenimiento", 999.00, "2026-08-25")  # fuera del periodo, no debe contar
    _gasto(client, "Seguridad", 300.00, "2026-09-10")  # otra categoría, no debe contar

    report = client.get("/budgets/report", params={"periodo": "2026-09-01"}).json()
    assert len(report) == 1
    assert report[0]["categoria"] == "Mantenimiento"
    assert report[0]["monto_planeado"] == 5000.00
    assert report[0]["monto_real"] == 2000.00


def test_report_excludes_budget_from_a_different_month(client):
    _como("tesorero")
    client.post(
        "/budgets",
        json={"categoria": "Mantenimiento", "periodicidad": "mensual", "periodo": "2026-08-01", "monto_planeado": 5000.00},
    )

    report = client.get("/budgets/report", params={"periodo": "2026-09-01"}).json()
    assert report == []


def test_report_annual_budget_sums_expenses_across_the_whole_year(client):
    _como("tesorero")
    client.post(
        "/budgets",
        json={"categoria": "Jardinería", "periodicidad": "anual", "periodo": "2026-01-01", "monto_planeado": 24000.00},
    )
    _gasto(client, "Jardinería", 2000.00, "2026-03-01")
    _gasto(client, "Jardinería", 2000.00, "2026-11-01")
    _gasto(client, "Jardinería", 500.00, "2027-01-05")  # otro año, no debe contar

    report = client.get("/budgets/report", params={"periodo": "2026-06-01"}).json()  # cualquier mes de 2026
    assert len(report) == 1
    assert report[0]["periodicidad"] == "anual"
    assert report[0]["monto_real"] == 4000.00


def test_report_with_no_expenses_shows_zero_actual(client):
    _como("tesorero")
    client.post(
        "/budgets",
        json={"categoria": "Eventos", "periodicidad": "mensual", "periodo": "2026-09-01", "monto_planeado": 1000.00},
    )

    report = client.get("/budgets/report", params={"periodo": "2026-09-01"}).json()
    assert report[0]["monto_real"] == 0.0


def test_report_defaults_to_current_month_when_no_periodo_given(client):
    client.get("/tenant/clabe")  # crea las tablas de prueba
    response = client.get("/budgets/report")
    assert response.status_code == 200
