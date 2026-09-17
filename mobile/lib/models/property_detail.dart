class PropertyDetail {
  final String id;
  final String identificador;
  final String referenciaPago;
  final double saldoAFavor;

  PropertyDetail({
    required this.id,
    required this.identificador,
    required this.referenciaPago,
    required this.saldoAFavor,
  });

  factory PropertyDetail.fromJson(Map<String, dynamic> json) {
    return PropertyDetail(
      id: json['id'] as String,
      identificador: json['identificador'] as String,
      referenciaPago: json['referencia_pago'] as String,
      saldoAFavor: (json['saldo_a_favor'] as num).toDouble(),
    );
  }
}
