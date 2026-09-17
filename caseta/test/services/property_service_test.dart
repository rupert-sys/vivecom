import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/property_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('listarPropiedades pide GET /properties y decodifica id e identificador', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/properties');
      return http.Response(
        '[{"id": "p1", "identificador": "Casa 1", "referencia_pago": "0001", "saldo_a_favor": 0.0}]',
        200,
      );
    });
    final service = PropertyService(api: ApiClient(client: mockClient));

    final propiedades = await service.listarPropiedades('un-token');

    expect(propiedades, hasLength(1));
    expect(propiedades[0].identificador, 'Casa 1');
  });

  test('lanza ApiException si falla', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No autorizado"}', 401));
    final service = PropertyService(api: ApiClient(client: mockClient));

    expect(() => service.listarPropiedades('un-token'), throwsA(isA<ApiException>()));
  });
}
