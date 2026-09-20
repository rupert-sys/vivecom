import 'package:app_residente/services/announcement_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureAvisos = '''
[
  {"id": "a1", "titulo": "Corte de agua", "contenido": "Mañana 9am-1pm.", "fecha_publicacion": "2026-09-16T10:00:00", "leido": false},
  {"id": "a2", "titulo": "Asamblea", "contenido": "Próxima semana.", "fecha_publicacion": "2026-09-10T10:00:00", "leido": true}
]
''';

void main() {
  test('listarAvisos pide /announcements con el token y decodifica leido', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/announcements');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(_fixtureAvisos, 200);
    });
    final service = AnnouncementService(api: ApiClient(client: mockClient));

    final avisos = await service.listarAvisos('un-token');

    expect(avisos, hasLength(2));
    expect(avisos[0].titulo, 'Corte de agua');
    expect(avisos[0].leido, isFalse);
    expect(avisos[1].leido, isTrue);
  });

  test('marcarLeido pide POST /announcements/{id}/read con el token', () async {
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.toString(), 'http://localhost:8000/announcements/a1/read');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response('', 204);
    });
    final service = AnnouncementService(api: ApiClient(client: mockClient));

    await service.marcarLeido('a1', 'un-token');
  });

  test('lanza ApiException si falla marcarLeido', () async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "Esta acción es solo para residentes ligados a una vivienda"}', 400);
    });
    final service = AnnouncementService(api: ApiClient(client: mockClient));

    expect(() => service.marcarLeido('a1', 'un-token'), throwsA(isA<ApiException>()));
  });
}
