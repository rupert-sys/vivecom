import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/lost_found_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureObjetos = '''
[
  {"id": "l1", "publicado_por": "u1", "descripcion": "Llavero azul", "foto_url": null, "estado": "autorizado"}
]
''';

void main() {
  test('listarObjetos pide GET /lost-found y decodifica el estado', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/lost-found');
      return http.Response(_fixtureObjetos, 200);
    });
    final service = LostFoundService(api: ApiClient(client: mockClient));

    final objetos = await service.listarObjetos('un-token');

    expect(objetos, hasLength(1));
    expect(objetos[0].descripcion, 'Llavero azul');
    expect(objetos[0].estado, 'autorizado');
    expect(objetos[0].fotoUrl, isNull);
  });

  test('publicarObjeto envía descripción y foto_url opcional', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/lost-found');
      expect(request.body, '{"descripcion":"Bici roja","foto_url":"http://x.mx/foto.jpg"}');
      return http.Response(
        '{"id": "l2", "publicado_por": "u1", "descripcion": "Bici roja", "foto_url": "http://x.mx/foto.jpg", "estado": "pendiente_autorizacion"}',
        201,
      );
    });
    final service = LostFoundService(api: ApiClient(client: mockClient));

    final objeto = await service.publicarObjeto('Bici roja', 'http://x.mx/foto.jpg', 'un-token');

    expect(objeto.estado, 'pendiente_autorizacion');
  });

  test('publicarObjeto omite foto_url cuando es nulo', () async {
    final mockClient = MockClient((request) async {
      expect(request.body, '{"descripcion":"Llaves"}');
      return http.Response(
        '{"id": "l3", "publicado_por": "u1", "descripcion": "Llaves", "foto_url": null, "estado": "pendiente_autorizacion"}',
        201,
      );
    });
    final service = LostFoundService(api: ApiClient(client: mockClient));

    await service.publicarObjeto('Llaves', null, 'un-token');
  });

  test('lanza ApiException si publicar falla', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No autorizado"}', 401));
    final service = LostFoundService(api: ApiClient(client: mockClient));

    expect(() => service.publicarObjeto('Llaves', null, 'un-token'), throwsA(isA<ApiException>()));
  });
}
