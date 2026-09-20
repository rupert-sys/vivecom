import 'package:app_residente/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('ApiClient', () {
    test('get() decodifica el JSON de una respuesta exitosa', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.toString(), 'http://localhost:8000/properties/p1/statement');
        expect(request.headers['Authorization'], 'Bearer un-token');
        return http.Response('{"identificador": "Casa 1"}', 200);
      });
      final api = ApiClient(client: mockClient);

      final data = await api.get('/properties/p1/statement', token: 'un-token');

      expect(data['identificador'], 'Casa 1');
    });

    test('lanza ApiException con el detail cuando el backend regresa un string', () async {
      final mockClient = MockClient((request) async {
        return http.Response('{"detail": "Credenciales inválidas"}', 401);
      });
      final api = ApiClient(client: mockClient);

      expect(
        () => api.post('/auth/login', {'email': 'a@a.com', 'password': 'x'}),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Credenciales inválidas')),
      );
    });

    test('lanza ApiException con el primer mensaje cuando el detail es una lista (422 de Pydantic)', () async {
      final mockClient = MockClient((request) async {
        return http.Response('{"detail": [{"msg": "value is not a valid email address"}]}', 422);
      });
      final api = ApiClient(client: mockClient);

      expect(
        () => api.post('/auth/login', {'email': 'no-es-email', 'password': 'x'}),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'value is not a valid email address')),
      );
    });

    test('usa un mensaje genérico si la respuesta de error no trae JSON válido', () async {
      final mockClient = MockClient((request) async {
        return http.Response('Bad Gateway', 502);
      });
      final api = ApiClient(client: mockClient);

      expect(
        () => api.get('/properties/p1/statement'),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Ocurrió un error inesperado.')),
      );
    });
  });
}
