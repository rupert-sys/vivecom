import 'package:app_residente/screens/clabe_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/clabe_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureClabe = '{"id": "t1", "nombre": "Residencial Las Torres", "clabe_destino": "646180157012345678"}';

void main() {
  Future<void> pumpClabe(WidgetTester tester, ClabeService service) async {
    await tester.pumpWidget(
      MaterialApp(
        home: ClabeScreen(token: 'un-token', clabeService: service),
      ),
    );
  }

  testWidgets('muestra el nombre del condominio y la CLABE vigente', (tester) async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/tenant/clabe');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(_fixtureClabe, 200);
    });
    final service = ClabeService(api: ApiClient(client: mockClient));

    await pumpClabe(tester, service);
    await tester.pumpAndSettle();

    expect(find.text('Residencial Las Torres'), findsOneWidget);
    expect(find.text('646180157012345678'), findsOneWidget);
  });

  testWidgets('el botón de copiar pone la CLABE en el portapapeles', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureClabe, 200));
    final service = ClabeService(api: ApiClient(client: mockClient));

    String? textoCopiado;
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
      if (call.method == 'Clipboard.setData') {
        textoCopiado = (call.arguments as Map)['text'] as String;
      }
      return null;
    });
    addTearDown(() => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, null));

    await pumpClabe(tester, service);
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.copy));
    await tester.pump();

    expect(textoCopiado, '646180157012345678');
    expect(find.text('CLABE copiada'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si falla la carga', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "Condominio no encontrado"}', 404));
    final service = ClabeService(api: ApiClient(client: mockClient));

    await pumpClabe(tester, service);
    await tester.pumpAndSettle();

    expect(find.text('Condominio no encontrado'), findsOneWidget);
  });
}
