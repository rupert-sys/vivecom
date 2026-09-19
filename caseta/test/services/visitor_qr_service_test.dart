import 'dart:convert';

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

  test('decodifica el tipo, la descripción y la vivienda de un código de proveedor', () async {
    final mockClient = MockClient((request) async => http.Response(
          '{"valido": true, "motivo": null, "property_id": "p4", "tipo": "proveedor", "descripcion": "Plomería López", "vivienda": "Casa 4"}',
          200,
        ));

    final resultado = await VisitorQrService(api: ApiClient(client: mockClient)).validar('abc', 't');

    expect((resultado.tipo, resultado.descripcion, resultado.vivienda), ('proveedor', 'Plomería López', 'Casa 4'));
  });

  test('emitirCodigoProveedor pide POST /visitor-qr/provider con la descripción y la vivienda', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/visitor-qr/provider');
      expect(request.headers['Authorization'], 'Bearer un-token');
      expect(jsonDecode(request.body), {'descripcion': 'Jardinería', 'property_id': 'p1'});
      return http.Response(
        '{"id": "q1", "property_id": "p1", "codigo": "abc", "usado": false, "fecha_generado": "2026-09-18T10:00:00", '
        '"fecha_usado": null, "tipo": "proveedor", "descripcion": "Jardinería"}',
        201,
      );
    });

    final codigo = await VisitorQrService(api: ApiClient(client: mockClient)).emitirCodigoProveedor('Jardinería', 'p1', 'un-token');

    expect((codigo.codigo, codigo.descripcion, codigo.propertyId), ('abc', 'Jardinería', 'p1'));
  });
}
