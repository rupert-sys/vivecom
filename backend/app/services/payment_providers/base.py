"""
Interfaz común para proveedores de recepción de depósitos SPEI. El objetivo
es poder cambiar de STP a Fintoc (o viceversa) sin tocar el resto del
código — solo se cambia qué implementación se usa en el endpoint del webhook.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DepositoRecibido:
    """Representación normalizada de un depósito, sin importar el proveedor."""

    monto: float
    referencia_numerica: str
    clave_rastreo: str
    fecha: datetime
    cuenta_beneficiaria: str  # la CLABE que recibió el depósito — identifica a qué tenant pertenece
    remitente_nombre: str | None = None


class PaymentProvider(ABC):
    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers) -> bool:
        """
        Valida que el webhook realmente venga del proveedor (no de un tercero).
        `headers` debe ser algo con `.get()` insensible a mayúsculas/minúsculas
        (ej. starlette.datastructures.Headers) — NUNCA un dict() plano
        convertido de eso, porque pierde esa insensibilidad y los headers
        HTTP llegan casi siempre en minúsculas.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_deposit_notification(self, payload: dict) -> DepositoRecibido:
        """Convierte el payload crudo del proveedor a nuestro formato normalizado."""
        raise NotImplementedError
