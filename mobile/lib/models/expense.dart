class Expense {
  final String id;
  final String categoria;
  final double monto;
  final String comprobanteUrl;
  final DateTime fecha; // solo fecha, sin hora — backend manda YYYY-MM-DD

  Expense({
    required this.id,
    required this.categoria,
    required this.monto,
    required this.comprobanteUrl,
    required this.fecha,
  });

  factory Expense.fromJson(Map<String, dynamic> json) {
    return Expense(
      id: json['id'] as String,
      categoria: json['categoria'] as String,
      monto: (json['monto'] as num).toDouble(),
      comprobanteUrl: json['comprobante_url'] as String,
      fecha: DateTime.parse(json['fecha'] as String),
    );
  }
}
