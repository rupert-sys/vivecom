import '../models/tenant_config.dart';
import 'api_client.dart';

class TenantService {
  final ApiClient _api;

  TenantService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<TenantConfig> obtenerConfiguracion(String token) async {
    final data = await _api.get('/tenant', token: token);
    return TenantConfig.fromJson(data as Map<String, dynamic>);
  }
}
