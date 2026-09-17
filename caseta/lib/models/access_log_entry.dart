import '../utils/dates.dart';

class AccessLogEntry {
  final String id;
  final String? propertyId;
  final String tipo;
  final DateTime horaEntrada;
  final DateTime? horaSalida;
  final List<String> placas;

  AccessLogEntry({
    required this.id,
    required this.propertyId,
    required this.tipo,
    required this.horaEntrada,
    required this.horaSalida,
    required this.placas,
  });

  factory AccessLogEntry.fromJson(Map<String, dynamic> json) {
    return AccessLogEntry(
      id: json['id'] as String,
      propertyId: json['property_id'] as String?,
      tipo: json['tipo'] as String,
      horaEntrada: utcNaiveToDateTime(json['hora_entrada'] as String),
      horaSalida: json['hora_salida'] != null ? utcNaiveToDateTime(json['hora_salida'] as String) : null,
      placas: (json['placas'] as List).cast<String>(),
    );
  }
}
