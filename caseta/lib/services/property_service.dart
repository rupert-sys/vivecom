import '../models/property.dart';
import 'api_client.dart';

class PropertyService {
  final ApiClient _api;

  PropertyService({ApiClient? api}) : _api = api ?? ApiClient();

  // GET /properties está abierto a cualquier rol autenticado del tenant
  // (incluye guardia) — así arma el selector de vivienda de F2-08.
  Future<List<Property>> listarPropiedades(String token) async {
    final data = await _api.get('/properties', token: token) as List;
    return data.map((e) => Property.fromJson(e as Map<String, dynamic>)).toList();
  }
}
