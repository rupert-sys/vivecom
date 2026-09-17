import 'package:app_caseta/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('ApiClient get() decodifica el JSON de una respuesta exitosa', () async {
    final client = ApiClient(client: MockClient((r) async => http.Response('{"ok": true}', 200)));
    final data = await client.get('/algo');
    expect(data, {'ok': true});
  });

  test('ApiClient lanza ApiException con el detail y statusCode cuando el backend regresa un string', () async {
    final client = ApiClient(client: MockClient((r) async => http.Response('{"detail": "No autorizado"}', 401)));
    try {
      await client.get('/algo');
      fail('debería haber lanzado ApiException');
    } on ApiException catch (err) {
      expect(err.message, 'No autorizado');
      expect(err.statusCode, 401);
    }
  });

  test('ApiClient lanza ApiException con el primer mensaje cuando el detail es una lista (422 de Pydantic)', () async {
    final client = ApiClient(
      client: MockClient((r) async => http.Response('{"detail": [{"msg": "campo requerido"}]}', 422)),
    );
    expect(() => client.get('/algo'), throwsA(isA<ApiException>().having((e) => e.message, 'message', 'campo requerido')));
  });

  test('ApiClient usa un mensaje genérico si la respuesta de error no trae JSON válido', () async {
    final client = ApiClient(client: MockClient((r) async => http.Response('gateway timeout', 502)));
    expect(
      () => client.get('/algo'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Ocurrió un error inesperado.')),
    );
  });
}
