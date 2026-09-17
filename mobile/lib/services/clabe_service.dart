import '../models/tenant_clabe.dart';
import 'api_client.dart';

class ClabeService {
  final ApiClient _api;

  ClabeService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<TenantClabe> obtenerClabe(String token) async {
    final data = await _api.get('/tenant/clabe', token: token);
    return TenantClabe.fromJson(data as Map<String, dynamic>);
  }
}
