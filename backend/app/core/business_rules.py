"""
Valores por defecto de la plataforma, iguales para TODOS los condominios que
no configuraron su reglamento. Cada condominio puede sobrescribir el recargo,
el plazo de pago y demás reglas con su `ReglamentoConfig` (models/reglamento.py,
PATCH /tenant/reglamento) — el reglamento interior manda sobre este default.
Ver alcance, sección 3.1 y sección 9 (pendiente "Recargo en cuotas bimestrales" resuelto).
"""

# Recargo por mora por defecto, aplicado a partir del minuto 1 del día 6 de cada mes.
RECARGO_PORCENTAJE = 0.10
RECARGO_DIA_DEL_MES = 6

# Cuota mínima mensual de Vivecom: equivalente a 50 viviendas, $25 MXN c/u, IVA incluido.
PRECIO_POR_VIVIENDA_MXN = 25.00
VIVIENDAS_MINIMAS_FACTURABLES = 50

# Reglas de reservación de amenidades.
RESERVACION_ANTICIPACION_MINIMA_DIAS = 2

# Quorum de votaciones.
VOTACION_QUORUM_MINIMO = 0.51
VOTACION_REACTIVACION_DIAS = 7
