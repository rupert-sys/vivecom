import 'dart:convert';

import 'package:app_residente/models/announcement.dart';
import 'package:app_residente/services/announcement_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

String _duda({
  String id = 'q1',
  bool propia = true,
  String estado = 'abierta',
  String? respuesta,
  bool nueva = false,
}) =>
    '{"id": "$id", "announcement_id": "a1", "aviso_titulo": "Corte de agua", "texto": "¿Habrá agua en la caseta?", '
    '"estado": "$estado", "respuesta": ${respuesta == null ? 'null' : '"$respuesta"'}, "respondido_en": null, '
    '"publica": false, "created_at": "2026-09-18T15:00:00", "propia": $propia, "vivienda": null, "respuesta_nueva": $nueva}';

void main() {
  test('listarDudas pide las dudas del aviso y decodifica la respuesta nueva y si es propia', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/announcements/a1/questions');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(
        '[${_duda(estado: 'respondida', respuesta: 'Sí, hay cisterna.', nueva: true)}, ${_duda(id: 'q2', propia: false)}]',
        200,
      );
    });

    final dudas = await AnnouncementService(api: ApiClient(client: mockClient)).listarDudas('a1', 'un-token');

    expect(
      (dudas[0].propia, dudas[0].respondida, dudas[0].respuestaNueva, dudas[0].respuesta),
      (true, true, true, 'Sí, hay cisterna.'),
    );
    expect(dudas[1].propia, isFalse);
    expect(dudas[0].createdAt.isUtc, isTrue); // naive-UTC del backend
  });

  test('preguntar manda el texto sin espacios de sobra', () async {
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/announcements/a1/questions');
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(_duda(), 201);
    });

    final duda = await AnnouncementService(api: ApiClient(client: mockClient)).preguntar('a1', '  ¿Habrá agua?  ', 't');

    expect(cuerpo, {'texto': '¿Habrá agua?'});
    expect(duda.estado, 'abierta');
  });

  test('preguntar lanza ApiException con el motivo del backend (tope, plazo cerrado)', () async {
    final mockClient = MockClient(
      (request) async => http.Response(
        '{"detail": "Ya tienes 3 dudas sin responder sobre este aviso; espera a que te contesten."}',
        409,
      ),
    );

    expect(
      AnnouncementService(api: ApiClient(client: mockClient)).preguntar('a1', 'x', 't'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('3 dudas sin responder'))),
    );
  });

  test('listarMisDudas pide las de mi vivienda', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/announcement-questions/mine');
      return http.Response('[${_duda(nueva: true, estado: 'respondida', respuesta: 'Sí')}]', 200);
    });

    final mias = await AnnouncementService(api: ApiClient(client: mockClient)).listarMisDudas('t');

    expect(mias.single.respuestaNueva, isTrue);
  });

  test('marcarRespuestasVistas solo pide las de ese aviso', () async {
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/announcement-questions/mine/seen');
      expect(request.url.queryParameters['announcement_id'], 'a1');
      return http.Response('', 204);
    });

    await AnnouncementService(api: ApiClient(client: mockClient)).marcarRespuestasVistas('a1', 't');
  });

  test('un aviso decodifica si admite dudas y si siguen abiertas', () {
    final abierto = Announcement.fromJson(
      jsonDecode(
        '{"id": "a1", "titulo": "T", "contenido": "C", "fecha_publicacion": "2026-09-16T10:00:00", "leido": false, '
        '"permite_dudas": true, "dudas_hasta": "2026-09-30", "dudas_abiertas": true}',
      ) as Map<String, dynamic>,
    );
    final viejo = Announcement.fromJson(
      jsonDecode(
        '{"id": "a2", "titulo": "T", "contenido": "C", "fecha_publicacion": "2026-09-16T10:00:00", "leido": true}',
      ) as Map<String, dynamic>,
    );

    expect((abierto.permiteDudas, abierto.dudasAbiertas), (true, true));
    expect((viejo.permiteDudas, viejo.dudasAbiertas), (false, false)); // un aviso anterior a las dudas
  });
}
