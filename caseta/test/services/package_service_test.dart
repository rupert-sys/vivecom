import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/package_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('listarEnCaseta pide solo los pendientes y decodifica cada paquete', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/packages');
      expect(request.url.queryParameters['pendientes'], 'true');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(
        '[{"id": "k1", "property_id": "p1", "fecha_llegada": "2026-09-18T15:30:00", "fecha_recogido": null}]',
        200,
      );
    });

    final paquetes = await PackageService(api: ApiClient(client: mockClient)).listarEnCaseta('un-token');

    expect(paquetes.single.id, 'k1');
    expect(paquetes.single.propertyId, 'p1');
    expect(paquetes.single.fechaLlegada.isUtc, isTrue); // naive-UTC del backend
  });

  test('marcarEntregado pide POST /packages/{id}/pickup', () async {
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/packages/k1/pickup');
      return http.Response('{"id": "k1"}', 200);
    });

    await PackageService(api: ApiClient(client: mockClient)).marcarEntregado('k1', 'un-token');
  });

  test('lanza ApiException si el paquete ya fue recogido', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "Este paquete ya fue recogido"}', 409));

    expect(
      PackageService(api: ApiClient(client: mockClient)).marcarEntregado('k1', 't'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Este paquete ya fue recogido')),
    );
  });
}
