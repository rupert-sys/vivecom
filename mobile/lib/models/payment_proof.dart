import '../utils/dates.dart';

// Comprobante de pago que el residente adjunta (captura o PDF del banco). No es un pago:
// tesorería lo revisa y, si el dinero llegó, lo acepta y se registra el pago.
class PaymentProof {
  final String id;
  final double monto;
  final DateTime? fechaPago; // solo fecha, la que dice el comprobante
  final String? nota;
  final String estado; // pendiente | aceptado | rechazado
  final DateTime createdAt;
  final String? motivoRechazo;
  final String archivoUrl; // enlace firmado de vida corta

  PaymentProof({
    required this.id,
    required this.monto,
    required this.fechaPago,
    required this.nota,
    required this.estado,
    required this.createdAt,
    required this.motivoRechazo,
    required this.archivoUrl,
  });

  factory PaymentProof.fromJson(Map<String, dynamic> json) {
    final fecha = json['fecha_pago'] as String?;
    return PaymentProof(
      id: json['id'] as String,
      monto: (json['monto'] as num).toDouble(),
      fechaPago: fecha == null ? null : DateTime.parse(fecha),
      nota: json['nota'] as String?,
      estado: json['estado'] as String,
      createdAt: utcNaiveToDateTime(json['created_at'] as String),
      motivoRechazo: json['motivo_rechazo'] as String?,
      archivoUrl: json['archivo_url'] as String,
    );
  }
}
