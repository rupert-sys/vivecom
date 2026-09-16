import sentry_sdk
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import (
    access_log, amenities, announcements, auth, budgets, expenses, fees, incidents, lost_found, packages, payments,
    payments_webhook, polls, privacy, properties, reports, reservations, residents, tenant_config, visitor_qr,
)
from app.core.config import settings

# F1-36: sentry_dsn vacío (default de desarrollo) deja el SDK inerte — no se
# manda nada a ningún lado hasta que haya un DSN real de producción.
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "API multi-tenant (schema por condominio en PostgreSQL) de Vivecom: administración de "
        "viviendas y residentes, cuotas y conciliación automática de pagos vía SPEI, gastos y "
        "presupuesto, avisos con confirmación de lectura, y control de accesos/paquetería. Ver "
        "alcance_vivecom.md y modelo_datos_vivecom.md en la raíz del repo para el detalle de "
        "producto y datos."
    ),
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(residents.router)
app.include_router(fees.router)
app.include_router(tenant_config.router)
app.include_router(payments.router)
app.include_router(payments_webhook.router)
app.include_router(expenses.router)
app.include_router(budgets.router)
app.include_router(reports.router)
app.include_router(announcements.router)
app.include_router(access_log.router)
app.include_router(visitor_qr.router)
app.include_router(packages.router)
app.include_router(incidents.router)
app.include_router(polls.router)
app.include_router(lost_found.router)
app.include_router(amenities.router)
app.include_router(reservations.router)
app.include_router(privacy.router)

# F1-36: expone /metrics en formato Prometheus/OpenMetrics (conteo y latencia
# por endpoint) — tanto Grafana+Prometheus como Datadog saben scrapear este
# formato directo, sin necesitar el agente propietario de Datadog aquí.
Instrumentator().instrument(app).expose(app, tags=["health"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "environment": settings.environment}
