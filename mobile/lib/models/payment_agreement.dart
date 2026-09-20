import '../utils/dates.dart';

class ScheduledPayment {
  final DateTime fecha; // solo fecha
  final double monto;

  ScheduledPayment({required this.fecha, required this.monto});

  factory ScheduledPayment.fromJson(Map<String, dynamic> json) {
    return ScheduledPayment(fecha: DateTime.parse(json['fecha'] as String), monto: (json['monto'] as num).toDouble());
  }
}

// Acuerdo de pago (prórroga de cuotas): el residente lo solicita por escrito, el comité lo acuerda y mientras
// se cumple la vivienda no cuenta como morosa (conserva voto y áreas comunes).
class PaymentAgreement {
  final String id;
  final String estado; // solicitado | vigente | rechazado | cumplido | incumplido | cancelado
  final String causa;
  final int propuestaPagos;
  final DateTime propuestaPrimerPago;
  final DateTime createdAt;
  final String? motivoRechazo;
  final List<ScheduledPayment> calendario; // vacío hasta que se aprueba
  final bool? congelaRecargo;
  final double? deudaInicial;
  final double? abonado;
  final double? pendienteCubierto;
  final ScheduledPayment? proximoPago;

  PaymentAgreement({
    required this.id,
    required this.estado,
    required this.causa,
    required this.propuestaPagos,
    required this.propuestaPrimerPago,
    required this.createdAt,
    required this.motivoRechazo,
    required this.calendario,
    required this.congelaRecargo,
    required this.deudaInicial,
    required this.abonado,
    required this.pendienteCubierto,
    required this.proximoPago,
  });

  bool get abierto => estado == 'solicitado' || estado == 'vigente';

  factory PaymentAgreement.fromJson(Map<String, dynamic> json) {
    final proximo = json['proximo_pago'] as Map<String, dynamic>?;
    return PaymentAgreement(
      id: json['id'] as String,
      estado: json['estado'] as String,
      causa: json['causa'] as String,
      propuestaPagos: json['propuesta_pagos'] as int,
      propuestaPrimerPago: DateTime.parse(json['propuesta_primer_pago'] as String),
      createdAt: utcNaiveToDateTime(json['created_at'] as String),
      motivoRechazo: json['motivo_rechazo'] as String?,
      calendario: ((json['calendario'] as List?) ?? const [])
          .map((e) => ScheduledPayment.fromJson(e as Map<String, dynamic>))
          .toList(),
      congelaRecargo: json['congela_recargo'] as bool?,
      deudaInicial: (json['deuda_inicial'] as num?)?.toDouble(),
      abonado: (json['abonado'] as num?)?.toDouble(),
      pendienteCubierto: (json['pendiente_cubierto'] as num?)?.toDouble(),
      proximoPago: proximo == null ? null : ScheduledPayment.fromJson(proximo),
    );
  }
}
