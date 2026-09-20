import 'package:app_residente/screens/lost_found_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/lost_found_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureObjetos = '''
[
  {"id": "l1", "publicado_por": "u1", "descripcion": "Llavero azul", "foto_url": null, "estado": "autorizado"}
]
''';

void main() {
  Future<void> pumpObjetos(WidgetTester tester, http.Client client) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LostFoundScreen(
            token: 'un-token',
            lostFoundService: LostFoundService(api: ApiClient(client: client)),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('lista las publicaciones autorizadas', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureObjetos, 200));

    await pumpObjetos(tester, mockClient);

    expect(find.text('Llavero azul'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay publicaciones', (tester) async {
    final mockClient = MockClient((request) async => http.Response('[]', 200));

    await pumpObjetos(tester, mockClient);

    expect(find.text('Todavía no hay publicaciones autorizadas.'), findsOneWidget);
  });

  testWidgets('publicar envía la descripción y limpia el formulario', (tester) async {
    final descripcionesPublicadas = <String>[];
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') {
        descripcionesPublicadas.add(request.body);
        return http.Response(
          '{"id": "l2", "publicado_por": "u1", "descripcion": "Bici roja", "foto_url": null, "estado": "pendiente_autorizacion"}',
          201,
        );
      }
      return http.Response(_fixtureObjetos, 200);
    });

    await pumpObjetos(tester, mockClient);

    await tester.enterText(find.byKey(const Key('descripcion_field')), 'Bici roja');
    await tester.tap(find.text('Publicar'));
    await tester.pumpAndSettle();

    expect(descripcionesPublicadas, ['{"descripcion":"Bici roja"}']);
    expect(find.text('Publicado. Aparecerá aquí cuando el administrador lo autorice.'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'Bici roja'), findsNothing);
  });

  testWidgets('muestra el error del backend si falla publicar', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') {
        return http.Response('{"detail": "Descripción muy corta"}', 422);
      }
      return http.Response(_fixtureObjetos, 200);
    });

    await pumpObjetos(tester, mockClient);

    await tester.enterText(find.byKey(const Key('descripcion_field')), 'x');
    await tester.tap(find.text('Publicar'));
    await tester.pumpAndSettle();

    expect(find.text('Descripción muy corta'), findsOneWidget);
  });
}
