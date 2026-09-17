import 'package:app_residente/screens/polls_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/poll_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

String _fixtureVotaciones({bool yaVoto = false, bool cerrada = false}) => '''
[
  {"id": "p1", "pregunta": "¿Aprobamos el reglamento?",
   "fecha_cierre": "${cerrada ? '2020-01-01' : '2099-01-01'}", "resultados_en_vivo": false,
   "quorum_alcanzado": false, "reactivada": false,
   "opciones": [{"id": "o1", "texto": "Sí"}, {"id": "o2", "texto": "No"}],
   "ya_voto": $yaVoto}
]
''';

void main() {
  Future<void> pumpVotaciones(WidgetTester tester, http.Client client) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PollsScreen(token: 'un-token', pollService: PollService(api: ApiClient(client: client))),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('lista las votaciones abiertas con su formulario de voto', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureVotaciones(), 200));

    await pumpVotaciones(tester, mockClient);

    expect(find.text('¿Aprobamos el reglamento?'), findsOneWidget);
    expect(find.text('Sí'), findsOneWidget);
    expect(find.text('Votar'), findsOneWidget);
  });

  testWidgets('votar elige una opción y llama al servicio', (tester) async {
    final llamadasVoto = <String>[];
    final mockClient = MockClient((request) async {
      if (request.method == 'POST' && request.url.path.endsWith('/vote')) {
        llamadasVoto.add(request.body);
        return http.Response('', 204);
      }
      return http.Response(_fixtureVotaciones(yaVoto: llamadasVoto.isNotEmpty), 200);
    });

    await pumpVotaciones(tester, mockClient);

    await tester.tap(find.byKey(const Key('opcion_o1')));
    await tester.pump();
    await tester.tap(find.text('Votar'));
    await tester.pumpAndSettle();

    expect(llamadasVoto, ['{"option_id":"o1"}']);
  });

  testWidgets('una votación en la que ya votó muestra el botón de ver resultados', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureVotaciones(yaVoto: true), 200));

    await pumpVotaciones(tester, mockClient);

    expect(find.text('Ya votaste. '), findsOneWidget);
    expect(find.text('Ver resultados'), findsOneWidget);
    expect(find.byKey(const Key('opcion_o1')), findsNothing);
  });

  testWidgets('ver resultados muestra el conteo por opción', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path.endsWith('/results')) {
        return http.Response(
          '{"poll_id": "p1", "total_votos": 2, "resultados": [{"option_id": "o1", "texto": "Sí", "votos": 2}, {"option_id": "o2", "texto": "No", "votos": 0}]}',
          200,
        );
      }
      return http.Response(_fixtureVotaciones(yaVoto: true), 200);
    });

    await pumpVotaciones(tester, mockClient);
    await tester.tap(find.text('Ver resultados'));
    await tester.pumpAndSettle();

    expect(find.text('Total de votos: 2'), findsOneWidget);
    expect(find.text('Sí: 2'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay votaciones', (tester) async {
    final mockClient = MockClient((request) async => http.Response('[]', 200));

    await pumpVotaciones(tester, mockClient);

    expect(find.text('Todavía no hay votaciones.'), findsOneWidget);
  });
}
