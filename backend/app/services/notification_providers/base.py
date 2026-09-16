"""
Interfaz común para el canal de notificaciones (F1-12: WhatsApp como canal
principal, SMS como respaldo si falla — ver alcance, sin correo electrónico).
Mismo espíritu que payment_providers/base.py: permite cambiar de proveedor
(Twilio, 360dialog) sin tocar el resto del código.
"""

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, telefono: str, mensaje: str) -> bool:
        """
        Intenta WhatsApp primero; si falla, cae a SMS (ver alcance F1-12).
        Devuelve True si se logró enviar por alguno de los dos canales.
        """
        raise NotImplementedError
