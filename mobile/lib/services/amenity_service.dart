import '../models/amenity.dart';
import 'api_client.dart';

class AmenityService {
  final ApiClient _api;

  AmenityService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<List<Amenity>> listarAmenidades(String token) async {
    final data = await _api.get('/amenities', token: token) as List;
    return data.map((e) => Amenity.fromJson(e as Map<String, dynamic>)).toList();
  }

  // Cuántos lugares quedan de la amenidad en un día y qué horarios ya están
  // tomados (ej. cajones de estacionamiento con capacidad > 1).
  Future<AmenityDayAvailability> obtenerDisponibilidadDelDia(String amenityId, DateTime fecha, String token) async {
    final dia = fecha.toIso8601String().split('T').first;
    final data = await _api.get('/amenities/$amenityId/disponibilidad?fecha=$dia', token: token);
    return AmenityDayAvailability.fromJson(data as Map<String, dynamic>);
  }

  Future<List<AmenityBusySlot>> obtenerDisponibilidad(String amenityId, String token) async {
    final data = await _api.get('/amenities/$amenityId/availability', token: token) as List;
    return data.map((e) => AmenityBusySlot.fromJson(e as Map<String, dynamic>)).toList();
  }
}
