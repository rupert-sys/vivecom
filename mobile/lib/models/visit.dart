import '../utils/dates.dart';

// Código de acceso de un solo uso que el residente le da a su visita
// (POST /visitor-qr, HU-S02): el guardia lo escanea en la caseta.
class VisitorQr {
  final String id;
  final String codigo;
  final bool usado;
  final DateTime fechaGenerado;
  final DateTime? fechaUsado;
  final String? nombreVisitante;
  final int? numeroPersonas;
  // qrPayload trae nombre/casa/residente/teléfono congelados al generarse: es lo que se codifica en la
  // imagen del QR (en vez del código pelón) para que el guardia lo pueda leer sin conexión.
  final String? qrPayload;

  VisitorQr({
    required this.id,
    required this.codigo,
    required this.usado,
    required this.fechaGenerado,
    required this.fechaUsado,
    this.nombreVisitante,
    this.numeroPersonas,
    this.qrPayload,
  });

  // Lo que la app codifica en la imagen del QR: el payload con los datos legibles sin conexión si existe
  // (código generado con esta versión), o el código pelón si no (compatibilidad con códigos viejos).
  String get datosParaElQr => qrPayload ?? codigo;

  factory VisitorQr.fromJson(Map<String, dynamic> json) {
    final usado = json['fecha_usado'] as String?;
    return VisitorQr(
      id: json['id'] as String,
      codigo: json['codigo'] as String,
      usado: json['usado'] as bool,
      fechaGenerado: utcNaiveToDateTime(json['fecha_generado'] as String),
      fechaUsado: usado == null ? null : utcNaiveToDateTime(usado),
      nombreVisitante: json['nombre_visitante'] as String?,
      numeroPersonas: json['numero_personas'] as int?,
      qrPayload: json['qr_payload'] as String?,
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
