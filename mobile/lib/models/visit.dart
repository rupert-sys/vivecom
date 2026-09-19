import '../utils/dates.dart';

// Código de acceso de un solo uso que el residente le da a su visita
// (POST /visitor-qr, HU-S02): el guardia lo escanea en la caseta.
class VisitorQr {
  final String id;
  final String codigo;
  final bool usado;
  final DateTime fechaGenerado;
  final DateTime? fechaUsado;

  VisitorQr({
    required this.id,
    required this.codigo,
    required this.usado,
    required this.fechaGenerado,
    required this.fechaUsado,
  });

  factory VisitorQr.fromJson(Map<String, dynamic> json) {
    final usado = json['fecha_usado'] as String?;
    return VisitorQr(
      id: json['id'] as String,
      codigo: json['codigo'] as String,
      usado: json['usado'] as bool,
      fechaGenerado: utcNaiveToDateTime(json['fecha_generado'] as String),
      fechaUsado: usado == null ? null : utcNaiveToDateTime(usado),
    );
  }
}

// Paquete registrado en la caseta para esta vivienda (HU-S05).
class PackageItem {
  final String id;
  final DateTime fechaLlegada;
  final DateTime? fechaRecogido;

  PackageItem({required this.id, required this.fechaLlegada, required this.fechaRecogido});

  bool get recogido => fechaRecogido != null;

  factory PackageItem.fromJson(Map<String, dynamic> json) {
    final recogido = json['fecha_recogido'] as String?;
    return PackageItem(
      id: json['id'] as String,
      fechaLlegada: utcNaiveToDateTime(json['fecha_llegada'] as String),
      fechaRecogido: recogido == null ? null : utcNaiveToDateTime(recogido),
    );
  }
}
