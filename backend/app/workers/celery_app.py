from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("vivecom", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.beat_schedule = {
    "generar-cargos-mensuales": {
        "task": "app.workers.tasks.generate_monthly_charges_task",
        # Corre todos los días a la 1am; la generación misma es idempotente
        # y solo crea cargos si aún no existen para el periodo, así que
        # correrlo de más no duplica nada — solo importa que corra el día 1.
        "schedule": crontab(hour=1, minute=0),
    },
    "aplicar-recargos-por-mora": {
        "task": "app.workers.tasks.apply_late_surcharges_task",
        # Corre diario justo después de medianoche, para capturar el "minuto
        # 1 del día 6" lo más cerca posible de la regla (alcance sección 3.1).
        "schedule": crontab(hour=0, minute=1),
    },
    "enviar-recordatorios-de-pago": {
        "task": "app.workers.tasks.send_payment_reminders_task",
        # Una vez al día, en horario razonable para mandar WhatsApp/SMS (no
        # de madrugada como los jobs anteriores, que son puro housekeeping).
        "schedule": crontab(hour=9, minute=0),
    },
    "enviar-confirmaciones-de-pago": {
        "task": "app.workers.tasks.send_payment_confirmations_task",
        # Cada 15 minutos: a diferencia del recordatorio, la confirmación sí
        # debe sentirse inmediata para quien acaba de pagar.
        "schedule": crontab(minute="*/15"),
    },
    "enviar-notificaciones-de-avisos": {
        "task": "app.workers.tasks.send_announcement_notifications_task",
        # Cada 15 minutos, igual que las confirmaciones de pago: un aviso
        # recién publicado (o programado que ya llegó a su fecha) debe
        # notificarse pronto, no esperar hasta el día siguiente.
        "schedule": crontab(minute="*/15"),
    },
    "enviar-notificaciones-de-paqueteria": {
        "task": "app.workers.tasks.send_package_notifications_task",
        # Cada 15 minutos: "me llegó un paquete" es exactamente el tipo de
        # aviso que sí debe sentirse inmediato (HU-S05).
        "schedule": crontab(minute="*/15"),
    },
    "procesar-cierre-de-votaciones": {
        "task": "app.workers.tasks.process_poll_closures_task",
        # Una vez al día basta: solo importa que corra el día de
        # fecha_cierre (o después), igual que generar-cargos-mensuales.
        "schedule": crontab(hour=1, minute=30),
    },
    "procesar-vencimiento-de-reservaciones": {
        "task": "app.workers.tasks.process_reservation_timeouts_task",
        # Cada 15 minutos: el rechazo automático por HU-C07 depende de un
        # periodo_limite_horas que puede ser tan corto como 1 hora — un
        # barrido diario lo dejaría vencer horas de más antes de reflejarlo.
        "schedule": crontab(minute="*/15"),
    },
}
celery_app.conf.timezone = "America/Mexico_City"
