class Fee {
  final String id;
  final double monto;
  final String periodicidad; // 'mensual' | 'bimestral'
  final DateTime activaDesde;

  Fee({required this.id, required this.monto, required this.periodicidad, required this.activaDesde});

  factory Fee.fromJson(Map<String, dynamic> json) {
    return Fee(
      id: json['id'] as String,
      monto: (json['monto'] as num).toDouble(),
      periodicidad: json['periodicidad'] as String,
      activaDesde: DateTime.parse(json['activa_desde'] as String),
    );
  }
}
