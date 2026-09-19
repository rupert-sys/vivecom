import '../utils/dates.dart';

class FeeChargeSummary {
  final String id;
  final DateTime periodo; // solo fecha, backend manda YYYY-MM-DD sin hora
  final double montoBase;
  final double recargoAplicado;
  final String estado;

  FeeChargeSummary({
    required this.id,
    required this.periodo,
    required this.montoBase,
    required this.recargoAplicado,
    required this.estado,
  });

  factory FeeChargeSummary.fromJson(Map<String, dynamic> json) {
    return FeeChargeSummary(
      id: json['id'] as String,
      periodo: DateTime.parse(json['periodo'] as String),
      montoBase: (json['monto_base'] as num).toDouble(),
      recargoAplicado: (json['recargo_aplicado'] as num).toDouble(),
      estado: json['estado'] as String,
    );
  }
}

class PaymentSummary {
  final String id;
  final double monto;
  final String estado;
  final DateTime fechaDeteccion;
  final String claveRastreo;

  PaymentSummary({
    required this.id,
    required this.monto,
    required this.estado,
    required this.fechaDeteccion,
    required this.claveRastreo,
  });

  factory PaymentSummary.fromJson(Map<String, dynamic> json) {
    return PaymentSummary(
      id: json['id'] as String,
      monto: (json['monto'] as num).toDouble(),
      estado: json['estado'] as String,
      fechaDeteccion: utcNaiveToDateTime(json['fecha_deteccion'] as String),
      claveRastreo: json['clave_rastreo'] as String,
    );
  }
}

class AccountStatement {
  final String propertyId;
  final String identificador;
  final double saldoAFavor;
  final double deudaTotal;
  final List<FeeChargeSummary> cargos;
  final List<PaymentSummary> pagos;
  // Cuotas vencidas según el reglamento, y lo que eso restringe a la vivienda.
  final bool enMora;
  final List<String> restriccionesPorMora;

  AccountStatement({
    required this.propertyId,
    required this.identificador,
    required this.saldoAFavor,
    required this.deudaTotal,
    required this.cargos,
    required this.pagos,
    this.enMora = false,
    this.restriccionesPorMora = const [],
  });

  factory AccountStatement.fromJson(Map<String, dynamic> json) {
    return AccountStatement(
      propertyId: json['property_id'] as String,
      identificador: json['identificador'] as String,
      saldoAFavor: (json['saldo_a_favor'] as num).toDouble(),
      deudaTotal: (json['deuda_total'] as num).toDouble(),
      cargos: (json['cargos'] as List).map((e) => FeeChargeSummary.fromJson(e as Map<String, dynamic>)).toList(),
      pagos: (json['pagos'] as List).map((e) => PaymentSummary.fromJson(e as Map<String, dynamic>)).toList(),
      enMora: (json['en_mora'] as bool?) ?? false,
      restriccionesPorMora: ((json['restricciones_por_mora'] as List?) ?? const []).map((e) => e as String).toList(),
    );
  }
}
