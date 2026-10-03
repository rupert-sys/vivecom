// Saldo de caja chica y caja grande del condominio (GET /cash-movements/balance, F0-12) — ingresos
// menos egresos de todo su historial. Mismo criterio de transparencia que ExpenseSummary: abierto
// a cualquier rol autenticado, el efectivo físico no es distinto de los gastos (HU-A12).
class CashBalance {
  final double chica;
  final double grande;

  CashBalance({required this.chica, required this.grande});

  factory CashBalance.fromJson(Map<String, dynamic> json) {
    return CashBalance(
      chica: (json['chica'] as num).toDouble(),
      grande: (json['grande'] as num).toDouble(),
    );
  }
}
