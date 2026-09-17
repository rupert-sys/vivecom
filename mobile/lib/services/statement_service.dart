import '../models/account_statement.dart';
import 'api_client.dart';

class StatementService {
  final ApiClient _api;

  StatementService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<AccountStatement> obtenerEstadoDeCuenta(String propertyId, String token) async {
    final data = await _api.get('/properties/$propertyId/statement', token: token);
    return AccountStatement.fromJson(data as Map<String, dynamic>);
  }
}
