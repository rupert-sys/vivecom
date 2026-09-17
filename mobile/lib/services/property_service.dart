import '../models/property_detail.dart';
import 'api_client.dart';

class PropertyService {
  final ApiClient _api;

  PropertyService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<PropertyDetail> obtenerPropiedad(String propertyId, String token) async {
    final data = await _api.get('/properties/$propertyId', token: token);
    return PropertyDetail.fromJson(data as Map<String, dynamic>);
  }
}
