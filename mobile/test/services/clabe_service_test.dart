import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/clabe_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('obtenerClabe pide /tenant/clabe con el token y decodifica la respuesta', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/tenant/clabe');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response('{"id": "t1", "nombre": "Residencial Las Torres", "clabe_destino": "646180157012345678"}', 200);
    });
    final service = ClabeService(api: ApiClient(client: mockClient));

    final clabe = await service.obtenerClabe('un-token');

    expect(clabe.id, 't1');
    expect(clabe.nombre, 'Residencial Las Torres');
    expect(clabe.clabeDestino, '646180157012345678');
  });
}
