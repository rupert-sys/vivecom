import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/visitor_qr_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('validar pide POST /visitor-qr/{codigo}/validate y decodifica un código válido', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/visitor-qr/abc123/validate');
      return http.Response('{"valido": true, "motivo": null, "property_id": "p1"}', 200);
    });
    final service = VisitorQrService(api: ApiClient(client: mockClient));

    final resultado = await service.validar('abc123', 'un-token');

    expect(resultado.valido, isTrue);
    expect(resultado.propertyId, 'p1');
  });

  test('decodifica un código ya usado', () async {
    final mockClient = MockClient((request) async => http.Response('{"valido": false, "motivo": "ya_usado", "property_id": null}', 200));
    final service = VisitorQrService(api: ApiClient(client: mockClient));

    final resultado = await service.validar('abc123', 'un-token');

    expect(resultado.valido, isFalse);
    expect(resultado.motivo, 'ya_usado');
  });
}
