"""
Configura un condominio con las reglas de su reglamento interior (Condominio
Arequipa, modificado el 18 de enero de 2026): cuota de $750 mensual con
tolerancia hasta el día 5, recargo de 5% mensual sobre saldo, efectivo
aceptado, morosos sin voto ni áreas comunes, gastos > $10,000 con asamblea y 3
cotizaciones, 7 cajones de visitas, y el área adoquinada (8 días de
anticipación, hasta la 01:00 am, cuota de $1,000).

Idempotente: se puede correr varias veces sobre el mismo schema.

Uso:
    python -m app.core.configurar_reglamento_arequipa tenant_4dbeb229
"""

import asyncio
import sys
from datetime import date, time

from sqlalchemy import select

from app.core.database import tenant_session
from app.core.migrate_schema import migrar_schema
from app.models.amenity import Amenity
from app.models.fee import Fee, Periodicidad
from app.models.reglamento import ReglamentoConfig

REGLAS = {
    "dia_limite_pago": 5,
    "recargo_porcentaje": 0.05,
    "recargo_modalidad": "mensual_sobre_saldo",
    "acepta_pago_efectivo": True,
    "morosos_sin_voto": True,
    "morosos_sin_areas_comunes": True,
    "gasto_umbral_asamblea": 10000,
    "cotizaciones_minimas": 3,
    "cajones_visitas": 7,
    "horas_max_estacionamiento_visitas": 24,
}

AREA_ADOQUINADA = {
    "nombre": "Área adoquinada",
    "periodo_limite_horas": 48,
    "dias_anticipacion_minimos": 8,
    "hora_fin_maxima": time(1, 0),
    "cuota": 1000,
    "notas_reglamento": "Reglamento Interior, Art. 2 III-VIII: solicitud con 8 días de anticipación, "
    "uso hasta la 01:00 am, cuota de $1,000 y sin adeudos pendientes.",
}


async def configurar(schema_name: str) -> None:
    await migrar_schema(schema_name)  # columnas nuevas, por si el schema aún no las tiene
    async with tenant_session(schema_name) as db:
        fila = (await db.execute(select(ReglamentoConfig).where(ReglamentoConfig.id == 1))).scalar_one_or_none()
        if fila is None:
            fila = ReglamentoConfig(id=1)
            db.add(fila)
        for campo, valor in REGLAS.items():
            setattr(fila, campo, valor)

        if (await db.execute(select(Fee).limit(1))).scalar_one_or_none() is None:
            db.add(Fee(monto=750, periodicidad=Periodicidad.mensual, activa_desde=date(2026, 1, 1)))

        area = (await db.execute(select(Amenity).where(Amenity.nombre == AREA_ADOQUINADA["nombre"]))).scalar_one_or_none()
        if area is None:
            db.add(Amenity(**AREA_ADOQUINADA))
        else:
            for campo, valor in AREA_ADOQUINADA.items():
                setattr(area, campo, valor)
        await db.commit()
    print(f"Reglamento de Arequipa aplicado al schema '{schema_name}'.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.core.configurar_reglamento_arequipa <schema_name>")
        sys.exit(1)
    asyncio.run(configurar(sys.argv[1]))
