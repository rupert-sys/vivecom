import '../models/expense.dart';
import 'api_client.dart';

class ExpenseService {
  final ApiClient _api;

  ExpenseService({ApiClient? api}) : _api = api ?? ApiClient();

  // GET /expenses (F1-15) es de lectura abierta a cualquier rol — HU-A12:
  // transparencia de gastos para cualquier residente, no solo el admin.
  Future<List<Expense>> listarGastos(
    String token, {
    DateTime? desde,
    DateTime? hasta,
    String? categoria,
  }) async {
    final params = <String, String>{};
    if (desde != null) params['desde'] = _isoFecha(desde);
    if (hasta != null) params['hasta'] = _isoFecha(hasta);
    if (categoria != null && categoria.trim().isNotEmpty) params['categoria'] = categoria.trim();

    final query = params.isEmpty
        ? ''
        : '?${params.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&')}';

    final data = await _api.get('/expenses$query', token: token) as List;
    return data.map((e) => Expense.fromJson(e as Map<String, dynamic>)).toList();
  }

  // GET /expenses/summary: ingresos, gastos y saldo del condominio, con los
  // mismos filtros de fecha que la lista.
  Future<ExpenseSummary> obtenerResumen(String token, {DateTime? desde, DateTime? hasta}) async {
    final params = <String, String>{};
    if (desde != null) params['desde'] = _isoFecha(desde);
    if (hasta != null) params['hasta'] = _isoFecha(hasta);
    final query = params.isEmpty ? '' : '?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}';
    final data = await _api.get('/expenses/summary$query', token: token);
    return ExpenseSummary.fromJson(data as Map<String, dynamic>);
  }

  String _isoFecha(DateTime d) => d.toIso8601String().split('T').first;
}
