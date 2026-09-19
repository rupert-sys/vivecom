import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/visit_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('generarCodigoDeVisita hace POST /visitor-qr con el token y decodifica el código', () async {
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/visitor-qr');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(
        '{"id": "q1", "property_id": "p1", "codigo": "abc123", "usado": false, '
        '"fecha_generado": "2026-09-18T10:00:00", "fecha_usado": null}',
        201,
      );
    });

    final qr = await VisitService(api: ApiClient(client: mockClient)).generarCodigoDeVisita('un-token');

    expect(qr.codigo, 'abc123');
    expect(qr.usado, isFalse);
    expect(qr.fechaGenerado.isUtc, isTrue); // naive-UTC del backend, interpretado como UTC
    expect(qr.fechaUsado, isNull);
  });

  test('listarMisCodigos decodifica los códigos usados con su fecha de uso', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/visitor-qr');
      return http.Response(
        '[{"id": "q1", "property_id": "p1", "codigo": "abc", "usado": true, '
        '"fecha_generado": "2026-09-18T10:00:00", "fecha_usado": "2026-09-18T11:30:00"}]',
        200,
      );
    });

    final codigos = await VisitService(api: ApiClient(client: mockClient)).listarMisCodigos('t');

    expect(codigos.single.usado, isTrue);
    expect(codigos.single.fechaUsado!.hour, 11);
  });

  test('listarMisPaquetes pide /packages/mine y distingue recogidos de pendientes', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/packages/mine');
      return http.Response(
        '[{"id": "k1", "property_id": "p1", "fecha_llegada": "2026-09-18T09:00:00", "fecha_recogido": null},'
        ' {"id": "k2", "property_id": "p1", "fecha_llegada": "2026-09-10T09:00:00", "fecha_recogido": "2026-09-11T18:00:00"}]',
        200,
      );
    });

    final paquetes = await VisitService(api: ApiClient(client: mockClient)).listarMisPaquetes('t');

    expect(paquetes.map((p) => p.recogido), [false, true]);
  });

  test('lanza ApiException si el backend rechaza generar el código', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "Solo para residentes"}', 400));

    expect(
      VisitService(api: ApiClient(client: mockClient)).generarCodigoDeVisita('t'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Solo para residentes')),
    );
  });
}
