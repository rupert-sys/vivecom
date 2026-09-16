"""
F1-15 / HU-A09: registro de gastos con comprobante obligatorio.
HU-A12: la lista es de lectura abierta (transparencia para residentes).
"""


def test_create_expense_requires_comprobante(client):
    response = client.post(
        "/expenses",
        json={"categoria": "Mantenimiento", "monto": 3200.00, "comprobante_url": "", "fecha": "2026-09-10"},
    )
    assert response.status_code == 422  # comprobante_url vacío no cuenta como "adjuntar comprobante"


def test_create_and_list_expense(client):
    created = client.post(
        "/expenses",
        json={
            "categoria": "Mantenimiento",
            "monto": 3200.00,
            "comprobante_url": "https://storage.example.com/comprobantes/abc.pdf",
            "fecha": "2026-09-10",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["categoria"] == "Mantenimiento"
    assert body["comprobante_url"].startswith("https://")

    listado = client.get("/expenses").json()
    assert len(listado) == 1
    assert listado[0]["id"] == body["id"]


def test_list_expenses_filters_by_category_and_date_range(client):
    client.post(
        "/expenses",
        json={
            "categoria": "Mantenimiento", "monto": 3200.00,
            "comprobante_url": "https://x/a.pdf", "fecha": "2026-08-15",
        },
    )
    client.post(
        "/expenses",
        json={
            "categoria": "Seguridad", "monto": 1800.00,
            "comprobante_url": "https://x/b.pdf", "fecha": "2026-09-05",
        },
    )

    solo_seguridad = client.get("/expenses", params={"categoria": "Seguridad"}).json()
    assert len(solo_seguridad) == 1
    assert solo_seguridad[0]["categoria"] == "Seguridad"

    solo_septiembre = client.get("/expenses", params={"desde": "2026-09-01", "hasta": "2026-09-30"}).json()
    assert len(solo_septiembre) == 1
    assert solo_septiembre[0]["categoria"] == "Seguridad"


def test_get_expense_by_id(client):
    created = client.post(
        "/expenses",
        json={
            "categoria": "Mantenimiento", "monto": 3200.00,
            "comprobante_url": "https://x/a.pdf", "fecha": "2026-09-10",
        },
    ).json()

    response = client.get(f"/expenses/{created['id']}")
    assert response.status_code == 200
    assert response.json()["monto"] == 3200.00


def test_get_unknown_expense_404(client):
    import uuid

    response = client.get(f"/expenses/{uuid.uuid4()}")
    assert response.status_code == 404
