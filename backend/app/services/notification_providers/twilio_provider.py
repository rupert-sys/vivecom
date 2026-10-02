"""
Implementación con Twilio: WhatsApp Business API como canal principal, SMS
como respaldo (F1-12).

⚠️ AVISO — LEER ANTES DE USAR EN PRODUCCIÓN:
A diferencia de STPProvider (payment_providers/stp.py), aquí sí se siguió la
documentación pública real de Twilio — la Messages API es la misma para SMS
y WhatsApp (https://www.twilio.com/docs/sms/send-messages,
https://www.twilio.com/docs/whatsapp/api), y es abierta: no requiere cuenta
dada de alta para consultarla. El formato del request (Basic Auth con
Account SID + Auth Token, POST a /2010-04-01/Accounts/{Sid}/Messages.json,
prefijo "whatsapp:" en From/To para ese canal) es correcto según esa
documentación — a diferencia de STP, esta parte SÍ está verificada.

Lo que SÍ falta y requiere una cuenta real antes de producción:
1. Un número de WhatsApp Business aprobado por Meta a través de Twilio
   (proceso de verificación que toma días, no es instantáneo).
2. Probar el envío real contra el sandbox de WhatsApp de Twilio.
3. Dar de alta Account SID / Auth Token / números de origen como secretos
   reales (ahora mismo app/core/config.py trae placeholders).
"""

import httpx

from app.services.notification_providers.base import NotificationProvider

_TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class TwilioProvider(NotificationProvider):
    def __init__(
        self, account_sid: str, auth_token: str, whatsapp_from: str, sms_from: str, api_base: str = _TWILIO_API_BASE
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.whatsapp_from = whatsapp_from
        self.sms_from = sms_from
        # Configurable (default: la API real de Twilio) para poder apuntar a un stub local en QA — ver
        # app/core/qa_notificaciones.py y Settings.twilio_api_base.
        self.api_base = api_base

    async def _enviar(self, de: str, para: str, mensaje: str) -> bool:
        """
        Revisión: un error de red (timeout, DNS, conexión rechazada) lanzaba
        la excepción de httpx hacia arriba, rompiendo el contrato de la
        interfaz (NotificationProvider.send() promete devolver bool, nunca
        lanzar) — un problema de conectividad transitorio con Twilio tumbaba
        al que llamó send() en vez de simplemente contar como "no se pudo
        enviar". Ahora cualquier error de httpx (no solo un status >= 300)
        se trata igual: intento fallido, no una excepción.
        """
        url = f"{self.api_base}/Accounts/{self.account_sid}/Messages.json"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url, auth=(self.account_sid, self.auth_token), data={"From": de, "To": para, "Body": mensaje}
                )
        except httpx.HTTPError:
            return False
        return response.status_code < 300

    async def send(self, telefono: str, mensaje: str) -> bool:
        enviado = await self._enviar(f"whatsapp:{self.whatsapp_from}", f"whatsapp:{telefono}", mensaje)
        if enviado:
            return True
        return await self._enviar(self.sms_from, telefono, mensaje)
