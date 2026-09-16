"""
Implementación para STP.

⚠️ AVISO IMPORTANTE — LEER ANTES DE USAR EN PRODUCCIÓN:
No tengo acceso a credenciales reales ni al sandbox de STP, así que el
formato exacto de los campos del webhook (nombres de llaves JSON, método de
firma) está basado en el patrón típico de proveedores de "conciliación en
tiempo real vía SPEI" (STP, Fintoc, Arcus) y en la documentación pública de
Banxico sobre el campo "referencia numérica" — NO está verificado contra la
documentación técnica real de STP, que requiere una cuenta dada de alta.

Antes de ir a producción, alguien con acceso a esa documentación técnica
(stp.mx/documentacion-tecnica) debe:
1. Confirmar los nombres reales de los campos en `parse_deposit_notification`.
2. Confirmar el método real de firma del webhook en `verify_webhook_signature`
   (aquí se implementó HMAC-SHA256 sobre el cuerpo crudo, que es el patrón
   más común en la industria, pero STP podría usar otro esquema).
3. Probar contra su ambiente de pruebas real.

Este archivo se entrega como una base sólida y funcional (parseo, matching de
referencia numérica, idempotencia), NO como una integración ya certificada.
"""

import hashlib
import hmac
from datetime import datetime

from app.services.payment_providers.base import DepositoRecibido, PaymentProvider


class STPProvider(PaymentProvider):
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def verify_webhook_signature(self, raw_body: bytes, headers) -> bool:
        firma_recibida = headers.get("X-STP-Signature", "")
        firma_esperada = hmac.new(
            self.webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(firma_recibida, firma_esperada)

    def parse_deposit_notification(self, payload: dict) -> DepositoRecibido:
        return DepositoRecibido(
            monto=float(payload["monto"]),
            referencia_numerica=str(payload["referenciaNumerica"]).zfill(7),
            clave_rastreo=payload["claveRastreo"],
            fecha=datetime.fromisoformat(payload["fechaOperacion"]),
            cuenta_beneficiaria=payload["cuentaBeneficiario"],
            remitente_nombre=payload.get("nombreOrdenante"),
        )
