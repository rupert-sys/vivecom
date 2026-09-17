import 'dart:convert';

import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/reservation_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureReservaciones = '''
[
  {"id": "r1", "amenity_id": "a1", "property_id": "p1", "fecha_inicio": "2026-10-01T10:00:00",
   "fecha_fin": "2026-10-01T12:00:00", "estado": "pendiente", "aprobador_id": null}
]
''';

void main() {
  test('listarMisReservaciones pide GET /reservations y decodifica fechas naive-UTC', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/reservations');
      return http.Response(_fixtureReservaciones, 200);
    });
    final service = ReservationService(api: ApiClient(client: mockClient));

    final reservaciones = await service.listarMisReservaciones('un-token');

    expect(reservaciones, hasLength(1));
    expect(reservaciones[0].estado, 'pendiente');
    expect(reservaciones[0].fechaInicio, DateTime.utc(2026, 10, 1, 10, 0, 0));
  });

  test('solicitarReservacion envía las fechas en UTC con sufijo Z', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/reservations');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['amenity_id'], 'a1');
      expect(body['fecha_inicio'], '2026-10-01T10:00:00.000Z');
      expect(body['fecha_fin'], '2026-10-01T12:00:00.000Z');
      return http.Response(
        '{"id": "r2", "amenity_id": "a1", "property_id": "p1", "fecha_inicio": "2026-10-01T10:00:00", "fecha_fin": "2026-10-01T12:00:00", "estado": "pendiente", "aprobador_id": null}',
        201,
      );
    });
    final service = ReservationService(api: ApiClient(client: mockClient));

    final reservacion = await service.solicitarReservacion(
      amenityId: 'a1',
      fechaInicio: DateTime.utc(2026, 10, 1, 10, 0, 0),
      fechaFin: DateTime.utc(2026, 10, 1, 12, 0, 0),
      token: 'un-token',
    );

    expect(reservacion.id, 'r2');
  });

  test('lanza ApiException si la reservación es rechazada por conflicto de horario', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "El horario ya está ocupado"}', 409));
    final service = ReservationService(api: ApiClient(client: mockClient));

    expect(
      () => service.solicitarReservacion(
        amenityId: 'a1',
        fechaInicio: DateTime.utc(2026, 10, 1, 10, 0, 0),
        fechaFin: DateTime.utc(2026, 10, 1, 12, 0, 0),
        token: 'un-token',
      ),
      throwsA(isA<ApiException>()),
    );
  });
}
