import '../utils/dates.dart';

class AccessLogEntry {
  final String id;
  final String? propertyId;
  final String tipo;
  final DateTime horaEntrada;
  final DateTime? horaSalida;
  final List<String> placas;
  final String? nombreVisitante;
  final int acompanantes;

  AccessLogEntry({
    required this.id,
    required this.propertyId,
    required this.tipo,
    required this.horaEntrada,
    required this.horaSalida,
    required this.placas,
    this.nombreVisitante,
    this.acompanantes = 0,
  });

  factory AccessLogEntry.fromJson(Map<String, dynamic> json) {
    return AccessLogEntry(
      id: json['id'] as String,
      propertyId: json['property_id'] as String?,
      tipo: json['tipo'] as String,
      horaEntrada: utcNaiveToDateTime(json['hora_entrada'] as String),
      horaSalida: json['hora_salida'] != null ? utcNaiveToDateTime(json['hora_salida'] as String) : null,
      placas: (json['placas'] as List).cast<String>(),
      nombreVisitante: json['nombre_visitante'] as String?,
      acompanantes: (json['acompanantes'] as int?) ?? 0,
    );
  }
}
