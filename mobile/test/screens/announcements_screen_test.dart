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
        home: AnnouncementsScreen(token: 'un-token', announcementService: AnnouncementService(api: ApiClient(client: client))),
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
}
