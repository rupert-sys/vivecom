import '../utils/dates.dart';

class Reservation {
  final String id;
  final String amenityId;
  final String propertyId;
  final DateTime fechaInicio;
  final DateTime fechaFin;
  final String estado; // pendiente | aprobada | rechazada | expirada
  final String? aprobadorId;
  final double cuota; // cuota de uso al solicitarla (0 = sin cuota)
  final bool cuotaPagada; // tesorería ya recibió la cuota

  Reservation({
    required this.id,
    required this.amenityId,
    required this.propertyId,
    required this.fechaInicio,
    required this.fechaFin,
    required this.estado,
    required this.aprobadorId,
    this.cuota = 0,
    this.cuotaPagada = false,
  });

  factory Reservation.fromJson(Map<String, dynamic> json) {
    return Reservation(
      id: json['id'] as String,
      amenityId: json['amenity_id'] as String,
      propertyId: json['property_id'] as String,
      // fecha_inicio/fecha_fin son naive-UTC (mismo patrón de F1-33): el
      // backend las guarda y regresa sin sufijo de zona.
      fechaInicio: utcNaiveToDateTime(json['fecha_inicio'] as String),
      fechaFin: utcNaiveToDateTime(json['fecha_fin'] as String),
      estado: json['estado'] as String,
      aprobadorId: json['aprobador_id'] as String?,
      cuota: (json['cuota'] as num?)?.toDouble() ?? 0,
      cuotaPagada: (json['cuota_pagada'] as bool?) ?? false,
    );
  }
}
