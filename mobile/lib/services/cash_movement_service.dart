import '../models/cash_balance.dart';
import 'api_client.dart';

class CashMovementService {
  final ApiClient _api;

  CashMovementService({ApiClient? api}) : _api = api ?? ApiClient();

  // GET /cash-movements/balance: lectura abierta a cualquier rol autenticado — misma
  // transparencia que el resumen financiero de gastos (HU-A12).
  Future<CashBalance> obtenerBalance(String token) async {
    final data = await _api.get('/cash-movements/balance', token: token);
    return CashBalance.fromJson(data as Map<String, dynamic>);
  }
}
