import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class PaymentAgreement(TenantBase):
    """
    Acuerdo de pago (prórroga de cuotas). El reglamento de Arequipa (Art. 1 VIII y Art. 9 VII) da al
    condómino el derecho de pedir por escrito una prórroga por causas justificadas y al comité la
    facultad de acordarla. No es "mover una fecha": es un acuerdo con causa, con calendario y con
    seguimiento — mientras se cumple, la vivienda no cuenta como morosa (conserva voto y áreas
    comunes) y, si el comité lo decide, su recargo se congela; si se incumple, vuelve a mora.

    Estados: solicitado → vigente → cumplido | incumplido ; solicitado → rechazado | cancelado ;
    vigente → cancelado. Una solicitud pendiente NO cambia nada: los efectos empiezan al aprobarse.
    """

    __tablename__ = "payment_agreement"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("property.id"), index=True)
    solicitado_por: Mapped[uuid.UUID] = mapped_column()
    # El escrito llegó en papel y el administrador lo capturó a nombre del vecino.
    capturado_por_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    causa: Mapped[str] = mapped_column(Text)
    archivo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stored_file.id"), nullable=True)
    # Lo que propone el residente: en cuántos pagos y desde cuándo (mensuales). 1 pago = "nueva fecha".
    propuesta_pagos: Mapped[int] = mapped_column(Integer)
    propuesta_primer_pago: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String, default="solicitado")
    created_at: Mapped[datetime] = mapped_column(DateTime)

    decidido_por: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    decidido_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String, nullable=True)

    # Lo acordado (se llena al aprobar). calendario: [{"fecha": "2026-10-05", "monto": 825.0}, ...]; el
    # ÚLTIMO pago significa "liquidar todo lo cubierto" aunque su monto sea otro (p. ej. si el recargo
    # siguió corriendo). cargos_cubiertos: los cargos sin pagar al aprobar — lo que cubre el acuerdo;
    # las cuotas que se generen después se pagan con normalidad.
    vigente_desde: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    calendario: Mapped[list | None] = mapped_column(JSON, nullable=True)
    congela_recargo: Mapped[bool] = mapped_column(Boolean, default=True)
    cargos_cubiertos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Los pagos confirmados que la vivienda ya tenía al aprobar: lo abonado al acuerdo es todo lo demás. No se
    # mide por fecha porque fecha_deteccion de un SPEI la pone el banco (hora local o solo el día), no nosotros.
    pagos_previos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    deuda_inicial: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
