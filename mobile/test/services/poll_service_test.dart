import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/poll_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureVotaciones = '''
[
  {"id": "p1", "pregunta": "¿Aprobamos el reglamento?", "fecha_cierre": "2026-12-31", "resultados_en_vivo": false,
   "quorum_alcanzado": false, "reactivada": false, "opciones": [{"id": "o1", "texto": "Sí"}, {"id": "o2", "texto": "No"}],
   "ya_voto": false}
]
''';

void main() {
  test('listarVotaciones pide /polls y decodifica opciones y ya_voto', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/polls');
      return http.Response(_fixtureVotaciones, 200);
    });
    final service = PollService(api: ApiClient(client: mockClient));

    final votaciones = await service.listarVotaciones('un-token');

    expect(votaciones, hasLength(1));
    expect(votaciones[0].pregunta, '¿Aprobamos el reglamento?');
    expect(votaciones[0].opciones, hasLength(2));
    expect(votaciones[0].yaVoto, isFalse);
  });

  test('votar pide POST /polls/{id}/vote con la opción elegida', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/polls/p1/vote');
      expect(request.body, '{"option_id":"o1"}');
      return http.Response('', 204);
    });
    final service = PollService(api: ApiClient(client: mockClient));

    await service.votar('p1', 'o1', 'un-token');
  });

  test('lanza ApiException si votar falla', () async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "Ya se registró un voto de esta vivienda"}', 409);
    });
    final service = PollService(api: ApiClient(client: mockClient));

    expect(() => service.votar('p1', 'o1', 'un-token'), throwsA(isA<ApiException>()));
  });

  test('obtenerResultados decodifica el conteo por opción', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/polls/p1/results');
      return http.Response(
        '{"poll_id": "p1", "total_votos": 3, "resultados": [{"option_id": "o1", "texto": "Sí", "votos": 2}, {"option_id": "o2", "texto": "No", "votos": 1}]}',
        200,
      );
    });
    final service = PollService(api: ApiClient(client: mockClient));

    final resultados = await service.obtenerResultados('p1', 'un-token');

    expect(resultados.totalVotos, 3);
    expect(resultados.resultados[0].votos, 2);
  });
}
