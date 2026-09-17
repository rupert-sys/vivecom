import 'package:app_caseta/services/access_log_service.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureAbierto = '''
[
  {"id": "a1", "property_id": "p1", "tipo": "visitante", "hora_entrada": "2026-10-01T10:00:00", "hora_salida": null, "placas": []},
  {"id": "a2", "property_id": null, "tipo": "proveedor", "hora_entrada": "2026-10-01T09:00:00", "hora_salida": "2026-10-01T09:30:00", "placas": []}
]
''';

void main() {
  test('listarAbiertos filtra los que ya tienen hora_salida', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/access-log');
      return http.Response(_fixtureAbierto, 200);
    });
    final service = AccessLogService(api: ApiClient(client: mockClient));

    final abiertos = await service.listarAbiertos('un-token');

    expect(abiertos, hasLength(1));
    expect(abiertos[0].id, 'a1');
  });

  test('registrarSalida pide POST /access-log/{id}/exit', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/access-log/a1/exit');
      expect(request.method, 'POST');
      return http.Response(
        '{"id": "a1", "property_id": "p1", "tipo": "visitante", "hora_entrada": "2026-10-01T10:00:00", "hora_salida": "2026-10-01T11:00:00", "placas": []}',
        200,
      );
    });
    final service = AccessLogService(api: ApiClient(client: mockClient));

    await service.registrarSalida('a1', 'un-token');
  });

  test('lanza ApiException si la salida ya estaba registrada (409)', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "Este acceso ya tiene salida registrada"}', 409));
    final service = AccessLogService(api: ApiClient(client: mockClient));

    expect(() => service.registrarSalida('a1', 'un-token'), throwsA(isA<ApiException>()));
  });
}
