"""
Reglas de las dudas de los residentes sobre un aviso. Un canal acotado, no un chat: una pregunta
recibe una respuesta, con un tope de dudas abiertas por vivienda y un plazo opcional por aviso.
"""

from datetime import date

from app.models.announcement import Announcement

# Dudas SIN responder que una vivienda puede tener a la vez sobre un mismo aviso.
MAX_DUDAS_ABIERTAS_POR_VIVIENDA = 3


def dudas_abiertas(aviso: Announcement, hoy: date) -> bool:
    """¿Se pueden mandar dudas sobre este aviso hoy? Activadas y dentro del plazo (el día límite incluido)."""
    return bool(aviso.permite_dudas) and (aviso.dudas_hasta is None or hoy <= aviso.dudas_hasta)
