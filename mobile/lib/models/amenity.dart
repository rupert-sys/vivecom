import '../utils/dates.dart';

class Amenity {
  final String id;
  final String nombre;
  final int periodoLimiteHoras;

  Amenity({required this.id, required this.nombre, required this.periodoLimiteHoras});

  factory Amenity.fromJson(Map<String, dynamic> json) {
    return Amenity(
      id: json['id'] as String,
      nombre: json['nombre'] as String,
      periodoLimiteHoras: json['periodo_limite_horas'] as int,
    );
  }
}

class AmenityBusySlot {
  final DateTime fechaInicio;
  final DateTime fechaFin;

  AmenityBusySlot({required this.fechaInicio, required this.fechaFin});

  factory AmenityBusySlot.fromJson(Map<String, dynamic> json) {
    return AmenityBusySlot(
      // fecha_inicio/fecha_fin son naive-UTC (mismo patrón de F1-33).
      fechaInicio: utcNaiveToDateTime(json['fecha_inicio'] as String),
      fechaFin: utcNaiveToDateTime(json['fecha_fin'] as String),
    );
  }
}
