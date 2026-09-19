import '../utils/dates.dart';

// Paquete que ya llegó y sigue en la caseta esperando a su residente.
class PackageEntry {
  final String id;
  final String propertyId;
  final DateTime fechaLlegada;

  PackageEntry({required this.id, required this.propertyId, required this.fechaLlegada});

  factory PackageEntry.fromJson(Map<String, dynamic> json) {
    return PackageEntry(
      id: json['id'] as String,
      propertyId: json['property_id'] as String,
      fechaLlegada: utcNaiveToDateTime(json['fecha_llegada'] as String),
    );
  }
}
