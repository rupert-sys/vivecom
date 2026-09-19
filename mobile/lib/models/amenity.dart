import '../utils/dates.dart';

class Amenity {
  final String id;
  final String nombre;
  final int periodoLimiteHoras;
  // Reglas propias del condominio para esta amenidad, ya redactadas en lenguaje
  // llano por el backend (ej. "Solicítala con al menos 8 días de anticipación.").
  final List<String> reglas;
  final double cuota; // 0 = sin cuota
  final int capacidad; // reservaciones que pueden coincidir en el mismo horario
  final String? notasReglamento;

  Amenity({
    required this.id,
    required this.nombre,
    required this.periodoLimiteHoras,
    this.reglas = const [],
    this.cuota = 0,
    this.capacidad = 1,
    this.notasReglamento,
  });

  factory Amenity.fromJson(Map<String, dynamic> json) {
    return Amenity(
      id: json['id'] as String,
      nombre: json['nombre'] as String,
      periodoLimiteHoras: json['periodo_limite_horas'] as int,
      reglas: ((json['reglas'] as List?) ?? const []).map((e) => e as String).toList(),
      cuota: (json['cuota'] as num?)?.toDouble() ?? 0,
      capacidad: (json['capacidad'] as int?) ?? 1,
      notasReglamento: json['notas_reglamento'] as String?,
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

// Disponibilidad de una amenidad en un día (GET /amenities/{id}/disponibilidad).
class AmenityDayAvailability {
  final int capacidad;
  final int cuposLibresTodoElDia; // lugares libres durante TODO el día
  final List<AmenityBusySlot> reservaciones;

  AmenityDayAvailability({required this.capacidad, required this.cuposLibresTodoElDia, required this.reservaciones});

  factory AmenityDayAvailability.fromJson(Map<String, dynamic> json) {
    return AmenityDayAvailability(
      capacidad: json['capacidad'] as int,
      cuposLibresTodoElDia: json['cupos_libres_todo_el_dia'] as int,
      reservaciones: (json['reservaciones'] as List)
          .map((e) => AmenityBusySlot.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
