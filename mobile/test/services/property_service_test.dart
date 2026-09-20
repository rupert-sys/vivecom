import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/property_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('obtenerPropiedad pide /properties/{id} con el token y decodifica la respuesta', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/properties/p1');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(
        '{"id": "p1", "identificador": "Casa 1", "referencia_pago": "0012345", "saldo_a_favor": 100.0}',
        200,
      );
    });
    final service = PropertyService(api: ApiClient(client: mockClient));

    final propiedad = await service.obtenerPropiedad('p1', 'un-token');

    expect(propiedad.id, 'p1');
    expect(propiedad.identificador, 'Casa 1');
    expect(propiedad.referenciaPago, '0012345');
    expect(propiedad.saldoAFavor, 100.0);
  });
}
