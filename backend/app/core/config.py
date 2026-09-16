from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno (.env en local, secrets en prod)."""

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Vivecom API"
    environment: str = "development"

    # Base de datos: un solo servidor PostgreSQL, un schema por tenant.
    database_url: str  # postgresql+asyncpg://user:pass@host:5432/vivecom
    control_schema: str = "public"  # schema donde vive la tabla `tenant`

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12 horas

    # Cola/jobs periódicos
    redis_url: str = "redis://localhost:6379/0"

    # Proveedor de recepción SPEI
    stp_webhook_secret: str = "cambia-esto-en-produccion"

    # Canal de notificaciones: WhatsApp Business API (Twilio) + SMS de respaldo (F1-12/F1-13)
    twilio_account_sid: str = "cambia-esto-en-produccion"
    twilio_auth_token: str = "cambia-esto-en-produccion"
    twilio_whatsapp_from: str = "+10000000000"  # número de WhatsApp Business aprobado por Twilio
    twilio_sms_from: str = "+10000000000"  # número SMS de respaldo

    # Logging y monitoreo en producción (F1-36). sentry_dsn vacío (default)
    # deja el SDK de Sentry inerte — no manda nada a ningún lado hasta que se
    # configure un DSN real. Las métricas (Datadog/Grafana) no necesitan
    # credencial aquí: se exponen en /metrics en formato Prometheus/OpenMetrics,
    # que ambos saben scrapear — lo que falta es apuntar un agente real ahí.
    sentry_dsn: str = ""


settings = Settings()
