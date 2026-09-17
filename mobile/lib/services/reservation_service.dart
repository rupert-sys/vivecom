import '../models/reservation.dart';
import 'api_client.dart';

class ReservationService {
  final ApiClient _api;

  ReservationService({ApiClient? api}) : _api = api ?? ApiClient();

  // Regresa solo las reservaciones de la propia vivienda del residente
  // (el backend ya filtra — ver GET /reservations en api/reservations.py).
  Future<List<Reservation>> listarMisReservaciones(String token) async {
    final data = await _api.get('/reservations', token: token) as List;
    return data.map((e) => Reservation.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Reservation> solicitarReservacion({
    required String amenityId,
    required DateTime fechaInicio,
    required DateTime fechaFin,
    required String token,
  }) async {
    final data = await _api.post(
      '/reservations',
      {
        'amenity_id': amenityId,
        // El backend ahora normaliza un datetime "aware" (con sufijo 'Z')
        // a naive-UTC antes de compararlo — no hace falta el truco de
        // quitar la Z a mano como en otras partes del proyecto (F2-19).
        'fecha_inicio': fechaInicio.toUtc().toIso8601String(),
        'fecha_fin': fechaFin.toUtc().toIso8601String(),
      },
      token: token,
    );
    return Reservation.fromJson(data as Map<String, dynamic>);
  }
}
