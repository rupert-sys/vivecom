import 'dart:convert';

import 'package:app_residente/screens/announcements_screen.dart';
import 'package:app_residente/services/announcement_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:flutter/material.dart';
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
  Future<void> pumpAvisos(WidgetTester tester, http.Client client) async {
    await tester.pumpWidget(
      MaterialApp(
        // AnnouncementsScreen ya no trae su propio Scaffold (vive dentro de
        // CommunityScreen, F2-19) — se envuelve aquí para probarla sola.
        home: Scaffold(
          body: AnnouncementsScreen(
            token: 'un-token',
            announcementService: AnnouncementService(api: ApiClient(client: client)),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('lista los avisos y marca los no leídos con un punto', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureAvisos, 200));

    await pumpAvisos(tester, mockClient);

    expect(find.text('Corte de agua'), findsOneWidget);
    expect(find.text('Asamblea'), findsOneWidget);
    expect(find.byKey(const Key('punto_no_leido')), findsOneWidget);
  });

  testWidgets('abrir un aviso no leído lo marca como leído', (tester) async {
    final llamadasMarcarLeido = <String>[];
    final mockClient = MockClient((request) async {
      if (request.method == 'POST' && request.url.path.endsWith('/read')) {
        llamadasMarcarLeido.add(request.url.pathSegments[1]);
        return http.Response('', 204);
      }
      return http.Response(_fixtureAvisos, 200);
    });

    await pumpAvisos(tester, mockClient);

    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();

    expect(llamadasMarcarLeido, ['a1']);
    expect(find.byKey(const Key('punto_no_leido')), findsNothing);
    expect(find.text('Mañana 9am-1pm.'), findsOneWidget);
  });

  testWidgets('abrir un aviso ya leído no vuelve a llamar marcarLeido', (tester) async {
    var llamadas = 0;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST' && request.url.path.endsWith('/read')) {
        llamadas++;
        return http.Response('', 204);
      }
      return http.Response(_fixtureAvisos, 200);
    });

    await pumpAvisos(tester, mockClient);

    await tester.tap(find.byKey(const Key('aviso_a2')));
    await tester.pumpAndSettle();

    expect(llamadas, 0);
    expect(find.text('Próxima semana.'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay avisos', (tester) async {
    final mockClient = MockClient((request) async => http.Response('[]', 200));

    await pumpAvisos(tester, mockClient);

    expect(find.text('Todavía no hay avisos.'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si falla la carga', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No autorizado"}', 401));

    await pumpAvisos(tester, mockClient);

    expect(find.text('No autorizado'), findsOneWidget);
  });

  dudasTests();
}

// ---------- Dudas sobre un aviso ----------

const _avisoConDudas =
    '{"id": "a1", "titulo": "Corte de agua", "contenido": "Mañana 9am-1pm.", "fecha_publicacion": "2026-09-16T10:00:00", "leido": true, '
    '"permite_dudas": true, "dudas_hasta": null, "dudas_abiertas": true}';

String _duda({
  String id = 'q1',
  String texto = '¿Habrá agua en la caseta?',
  bool propia = true,
  String estado = 'abierta',
  String? respuesta,
  bool nueva = false,
}) =>
    '{"id": "$id", "announcement_id": "a1", "aviso_titulo": "Corte de agua", "texto": "$texto", "estado": "$estado", '
    '"respuesta": ${respuesta == null ? 'null' : '"$respuesta"'}, "respondido_en": null, "publica": ${!propia}, '
    '"created_at": "2026-09-18T15:00:00", "propia": $propia, "vivienda": null, "respuesta_nueva": $nueva}';

Future<void> _pumpConDudas(WidgetTester tester, http.Client client, {ValueChanged<int>? onRespuestasNuevas}) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AnnouncementsScreen(
          token: 'un-token',
          announcementService: AnnouncementService(api: ApiClient(client: client)),
          onRespuestasNuevas: onRespuestasNuevas,
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void dudasTests() {
  testWidgets('un aviso con dudas muestra las aclaraciones públicas, mis dudas y el botón para preguntar', (
    tester,
  ) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/announcements') return http.Response('[$_avisoConDudas]', 200);
      if (request.url.path == '/announcements/a1/questions') {
        return http.Response(
          '[${_duda(id: 'p1', texto: '¿Aplica a la torre B?', propia: false, estado: 'respondida', respuesta: 'Solo torres A y C.')}, '
          '${_duda(id: 'q1', texto: 'Mi duda pendiente')}]',
          200,
        );
      }
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('aclaracion_p1')), findsOneWidget);
    expect(find.text('Administración: Solo torres A y C.'), findsOneWidget);
    expect(find.text('Sin responder todavía'), findsOneWidget);
    expect(find.byKey(const Key('duda_boton_a1')), findsOneWidget);
  });

  testWidgets('un aviso sin dudas no muestra esa sección ni la pide al servidor', (tester) async {
    final rutas = <String>[];
    final mockClient = MockClient((request) async {
      rutas.add(request.url.path);
      return http.Response(_fixtureAvisos, 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('dudas_a1')), findsNothing);
    expect(rutas.where((r) => r.endsWith('/questions')), isEmpty);
  });

  testWidgets('con el plazo vencido no se puede preguntar pero se siguen viendo las aclaraciones', (tester) async {
    final cerrado = _avisoConDudas.replaceFirst('"dudas_abiertas": true', '"dudas_abiertas": false');
    final mockClient = MockClient((request) async {
      if (request.url.path == '/announcements') return http.Response('[$cerrado]', 200);
      if (request.url.path == '/announcements/a1/questions') {
        return http.Response('[${_duda(id: 'p1', propia: false, estado: 'respondida', respuesta: 'Sí.')}]', 200);
      }
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('duda_boton_a1')), findsNothing);
    expect(find.byKey(const Key('dudas_cerradas')), findsOneWidget);
    expect(find.byKey(const Key('aclaracion_p1')), findsOneWidget);
  });

  testWidgets('mandar una duda: se escribe, se envía y aparece entre mis dudas', (tester) async {
    Map<String, dynamic>? cuerpo;
    var enviada = false;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/announcements') return http.Response('[$_avisoConDudas]', 200);
      if (request.method == 'POST' && request.url.path == '/announcements/a1/questions') {
        cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
        enviada = true;
        return http.Response(_duda(texto: '¿Cuánto durará?'), 201);
      }
      if (request.url.path == '/announcements/a1/questions') {
        return http.Response(enviada ? '[${_duda(texto: '¿Cuánto durará?')}]' : '[]', 200);
      }
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('duda_boton_a1')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('duda_texto_field')), '¿Cuánto durará?');
    await tester.tap(find.text('Enviar'));
    await tester.pumpAndSettle();

    expect(cuerpo, {'texto': '¿Cuánto durará?'});
    expect(find.byKey(const Key('duda_texto_field')), findsNothing); // el diálogo se cerró
    expect(find.text('¿Cuánto durará?'), findsOneWidget);
    expect(find.text('Sin responder todavía'), findsOneWidget);
  });

  testWidgets('no se envía una duda vacía', (tester) async {
    var posts = 0;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') posts++;
      if (request.url.path == '/announcements') return http.Response('[$_avisoConDudas]', 200);
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('duda_boton_a1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar'));
    await tester.pumpAndSettle();

    expect(find.text('Escribe tu duda.'), findsOneWidget);
    expect(posts, 0); // el aviso ya estaba leído y no se mandó ninguna duda
  });

  testWidgets('si el backend rechaza la duda (tope de 3), el diálogo sigue abierto con el motivo', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/announcements') return http.Response('[$_avisoConDudas]', 200);
      if (request.method == 'POST' && request.url.path == '/announcements/a1/questions') {
        return http.Response(
          '{"detail": "Ya tienes 3 dudas sin responder sobre este aviso; espera a que te contesten."}',
          409,
        );
      }
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('duda_boton_a1')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('duda_texto_field')), 'Otra más');
    await tester.tap(find.text('Enviar'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('error_duda')), findsOneWidget);
    expect(find.textContaining('3 dudas sin responder'), findsOneWidget);
    expect(find.byKey(const Key('duda_texto_field')), findsOneWidget);
  });

  testWidgets('la respuesta nueva se marca con "Nueva", se avisa al servidor y baja la insignia', (tester) async {
    final conteos = <int>[];
    String? avisoMarcado;
    var vistas = false;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/announcements') return http.Response('[$_avisoConDudas]', 200);
      if (request.method == 'POST' && request.url.path == '/announcement-questions/mine/seen') {
        avisoMarcado = request.url.queryParameters['announcement_id'];
        vistas = true;
        return http.Response('', 204);
      }
      if (request.url.path == '/announcement-questions/mine') {
        return http.Response('[${_duda(estado: 'respondida', respuesta: 'Sí, hay cisterna.', nueva: !vistas)}]', 200);
      }
      if (request.url.path == '/announcements/a1/questions') {
        return http.Response('[${_duda(estado: 'respondida', respuesta: 'Sí, hay cisterna.', nueva: true)}]', 200);
      }
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient, onRespuestasNuevas: conteos.add);
    expect(conteos.last, 1); // al abrir la pantalla ya sabe que hay una respuesta nueva
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('respuesta_nueva')), findsOneWidget);
    expect(find.text('Administración: Sí, hay cisterna.'), findsOneWidget);
    expect(avisoMarcado, 'a1');
    expect(conteos.last, 0);
  });

  testWidgets('si no cargan las dudas del aviso muestra el error y el aviso sigue legible', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/announcements') return http.Response('[$_avisoConDudas]', 200);
      if (request.url.path == '/announcements/a1/questions') return http.Response('{"detail": "Sin conexión"}', 503);
      return http.Response('[]', 200);
    });

    await _pumpConDudas(tester, mockClient);
    await tester.tap(find.byKey(const Key('aviso_a1')));
    await tester.pumpAndSettle();

    expect(find.text('Sin conexión'), findsOneWidget);
    expect(find.text('Mañana 9am-1pm.'), findsOneWidget);
  });
}
