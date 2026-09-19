import 'package:app_residente/services/amenity_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('listarAmenidades pide GET /amenities y decodifica cada amenidad', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/amenities');
      return http.Response('[{"id": "a1", "nombre": "Salón de fiestas", "periodo_limite_horas": 24}]', 200);
    });
    final service = AmenityService(api: ApiClient(client: mockClient));

    final amenidades = await service.listarAmenidades('un-token');

    expect(amenidades, hasLength(1));
    expect(amenidades[0].nombre, 'Salón de fiestas');
    expect(amenidades[0].periodoLimiteHoras, 24);
  });

  test('obtenerDisponibilidad decodifica los horarios ocupados', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/amenities/a1/availability');
      return http.Response(
        '[{"fecha_inicio": "2026-10-01T10:00:00", "fecha_fin": "2026-10-01T12:00:00"}]',
        200,
      );
    });
    final service = AmenityService(api: ApiClient(client: mockClient));

    final ocupados = await service.obtenerDisponibilidad('a1', 'un-token');

    expect(ocupados, hasLength(1));
    expect(ocupados[0].fechaInicio, DateTime.utc(2026, 10, 1, 10, 0, 0));
  });

  test('lanza ApiException si listar falla', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No autorizado"}', 401));
    final service = AmenityService(api: ApiClient(client: mockClient));

    expect(() => service.listarAmenidades('un-token'), throwsA(isA<ApiException>()));
  });

  test('decodifica las reglas, la cuota y la capacidad de una amenidad', () async {
    final mockClient = MockClient((request) async => http.Response(
          '[{"id": "a1", "nombre": "Cajones", "periodo_limite_horas": 24, "capacidad": 7, "cuota": 1000.0, '
          '"notas_reglamento": "Art. 2", "reglas": ["Solicítala con al menos 8 días de anticipación."]}]',
          200,
        ));
    final amenidades = await AmenityService(api: ApiClient(client: mockClient)).listarAmenidades('t');

    expect(amenidades.single.capacidad, 7);
    expect(amenidades.single.cuota, 1000.0);
    expect(amenidades.single.reglas, ['Solicítala con al menos 8 días de anticipación.']);
    expect(amenidades.single.notasReglamento, 'Art. 2');
  });

  test('obtenerDisponibilidadDelDia pide /disponibilidad con la fecha y decodifica los cupos', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/amenities/a1/disponibilidad');
      expect(request.url.queryParameters['fecha'], '2026-10-05');
      return http.Response(
        '{"amenity_id": "a1", "fecha": "2026-10-05", "capacidad": 3, "cupos_libres_todo_el_dia": 1, '
        '"reservaciones": [{"fecha_inicio": "2026-10-05T16:00:00", "fecha_fin": "2026-10-05T20:00:00"}], "reglas": []}',
        200,
      );
    });
    final disponibilidad = await AmenityService(api: ApiClient(client: mockClient))
        .obtenerDisponibilidadDelDia('a1', DateTime(2026, 10, 5, 15, 30), 't');

    expect(disponibilidad.capacidad, 3);
    expect(disponibilidad.cuposLibresTodoElDia, 1);
    expect(disponibilidad.reservaciones.single.fechaInicio.isUtc, isTrue);
  });
}
