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

class TotalPorConcepto {
  final String concepto;
  final double total;
  final int cantidad;

  TotalPorConcepto({required this.concepto, required this.total, required this.cantidad});

  factory TotalPorConcepto.fromJson(Map<String, dynamic> json) {
    return TotalPorConcepto(
      concepto: json['concepto'] as String,
      total: (json['total'] as num).toDouble(),
      cantidad: json['cantidad'] as int,
    );
  }
}

// Resumen financiero del condominio (GET /expenses/summary): cuánto entró,
// cuánto se gastó y el saldo — a favor si es positivo, en contra si no.
class ExpenseSummary {
  final double ingresos;
  final double gastos;
  final double saldo;
  final double porCobrar;
  final List<TotalPorConcepto> gastosPorCategoria;

  ExpenseSummary({
    required this.ingresos,
    required this.gastos,
    required this.saldo,
    required this.porCobrar,
    required this.gastosPorCategoria,
  });

  factory ExpenseSummary.fromJson(Map<String, dynamic> json) {
    return ExpenseSummary(
      ingresos: (json['ingresos'] as num).toDouble(),
      gastos: (json['gastos'] as num).toDouble(),
      saldo: (json['saldo'] as num).toDouble(),
      porCobrar: (json['por_cobrar'] as num).toDouble(),
      gastosPorCategoria: (json['gastos_por_categoria'] as List)
          .map((e) => TotalPorConcepto.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
