import '../models/amenity.dart';
import 'api_client.dart';

class AmenityService {
  final ApiClient _api;

  AmenityService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<List<Amenity>> listarAmenidades(String token) async {
    final data = await _api.get('/amenities', token: token) as List;
    return data.map((e) => Amenity.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<AmenityBusySlot>> obtenerDisponibilidad(String amenityId, String token) async {
    final data = await _api.get('/amenities/$amenityId/availability', token: token) as List;
    return data.map((e) => AmenityBusySlot.fromJson(e as Map<String, dynamic>)).toList();
  }
}
