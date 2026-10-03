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
    # F0-12: "Recordarme" en el login — sin guardar la contraseña en ningún lado, solo una sesión
    # mucho más larga (ver LoginRequest.recordar / create_access_token). 30 días, no indefinido:
    # un dispositivo perdido con la sesión abierta sigue expirando solo en algún momento.
    remembered_session_expire_minutes: int = 60 * 24 * 30  # 30 días

    # Cola/jobs periódicos
    redis_url: str = "redis://localhost:6379/0"

    # F1-18: orígenes permitidos para el panel admin (React) vía CORS. Lista
    # separada por comas; default cubre el puerto de Vite en local (5173).
    cors_origins: str = "http://localhost:5173"

    # Proveedor de recepción SPEI
    stp_webhook_secret: str = "cambia-esto-en-produccion"

    # Canal de notificaciones: WhatsApp Business API (Twilio) + SMS de respaldo (F1-12/F1-13)
    twilio_account_sid: str = "cambia-esto-en-produccion"
    twilio_auth_token: str = "cambia-esto-en-produccion"
    twilio_whatsapp_from: str = "+10000000000"  # número de WhatsApp Business aprobado por Twilio
    twilio_sms_from: str = "+10000000000"  # número SMS de respaldo
    # F1-35 (QA de entrega): apuntar a un stub local en vez de la API real de Twilio para poder inspeccionar
    # qué se habría mandado (destinatario, contenido, si cayó a SMS) sin una cuenta de Twilio real — ver
    # app/core/qa_notificaciones.py. En producción se deja el default real.
    twilio_api_base: str = "https://api.twilio.com/2010-04-01"

    # Almacenamiento de archivos (comprobantes de pago y de gastos). En desarrollo
    # se guardan en disco local; en producción, en S3 (STORAGE_BACKEND=s3) — un
    # contenedor tiene disco efímero, lo que se guarde ahí se pierde al redesplegar.
    storage_backend: str = "local"  # local | s3
    storage_local_dir: str = "./storage"
    # En producción el disco local se rechaza (fail-closed, ver file_storage.get_storage). Un despliegue en UNA
    # máquina con el directorio en un volumen persistente que además se respalda (deploy/) puede aceptarlo de
    # forma explícita con STORAGE_LOCAL_IN_PRODUCTION=true. En un contenedor sin volumen, NO.
    storage_local_in_production: bool = False
    storage_s3_bucket: str = ""
    storage_s3_region: str = "us-east-1"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB por archivo
    # Base de los enlaces firmados a archivos (los abre el navegador o la app, no la API).
    public_base_url: str = "http://localhost:8000"
    file_link_ttl_seconds: int = 60 * 60  # vigencia de un enlace firmado

    # Logging y monitoreo en producción (F1-36). sentry_dsn vacío (default)
    # deja el SDK de Sentry inerte — no manda nada a ningún lado hasta que se
    # configure un DSN real. Las métricas (Datadog/Grafana) no necesitan
    # credencial aquí: se exponen en /metrics en formato Prometheus/OpenMetrics,
    # que ambos saben scrapear — lo que falta es apuntar un agente real ahí.
    sentry_dsn: str = ""


settings = Settings()
