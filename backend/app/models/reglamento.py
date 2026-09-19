from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_base import TenantBase


class ReglamentoConfig(TenantBase):
    """
    Reglas del reglamento interior de UN condominio que cambian el
    comportamiento del sistema. Una sola fila por tenant (id = 1).

    Antes estas reglas eran globales de la plataforma (business_rules.py):
    el alcance decidió, con base en 2 entrevistas, que el recargo por mora
    era igual para todos. El reglamento real del Condominio Arequipa
    (modificado el 18-ene-2026) lo contradice — 5% mensual sobre saldos
    insolutos, se acepta efectivo, morosos sin voto ni áreas comunes — así
    que pasan a ser configurables por condominio. Los defaults de esta tabla
    reproducen las reglas globales de siempre: un tenant sin fila (o sin
    tocar) se comporta exactamente igual que antes.
    """

    __tablename__ = "reglamento_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Cuota (Art. 9): se paga en los primeros N días del mes; el recargo
    # arranca el día siguiente.
    dia_limite_pago: Mapped[int] = mapped_column(Integer, default=5)
    recargo_porcentaje: Mapped[float] = mapped_column(Numeric(6, 4), default=0.10)
    # "unico": un solo recargo (regla global histórica). "mensual_sobre_saldo":
    # el porcentaje se cobra de nuevo cada mes que la cuota sigue sin pagarse
    # (Arequipa Art. 9 I: "5% mensual sobre saldos insolutos").
    recargo_modalidad: Mapped[str] = mapped_column(String, default="unico")
    acepta_pago_efectivo: Mapped[bool] = mapped_column(Boolean, default=False)

    # Sanciones por mora (Art. 5 III, Art. 21).
    morosos_sin_voto: Mapped[bool] = mapped_column(Boolean, default=False)
    morosos_sin_areas_comunes: Mapped[bool] = mapped_column(Boolean, default=False)

    # Gastos (Art. 8 VII): arriba de este monto, los gastos programados y
    # extraordinarios necesitan asamblea y cotizaciones. None = sin umbral.
    gasto_umbral_asamblea: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    cotizaciones_minimas: Mapped[int] = mapped_column(Integer, default=3)

    # Estacionamiento de visitantes (Art. 2 IX-XIII, Art. 17 V.7). 0 = no aplica.
    cajones_visitas: Mapped[int] = mapped_column(Integer, default=0)
    horas_max_estacionamiento_visitas: Mapped[int] = mapped_column(Integer, default=24)
