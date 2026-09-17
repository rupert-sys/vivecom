import 'package:app_caseta/screens/qr_scan_screen.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/visitor_qr_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  Future<void> pumpPantalla(WidgetTester tester, http.Client client) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QrScanScreen(token: 'un-token', visitorQrService: VisitorQrService(api: ApiClient(client: client))),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  // El Simulador de iOS/entorno de pruebas no tiene cámara real: mobile_scanner
  // falla al inicializar su canal de plataforma y cae en errorBuilder — así que
  // estas pruebas cubren el flujo de código manual, que es el único
  // verificable sin hardware real (y el respaldo real para un guardia si la
  // cámara falla).
  testWidgets('valida un código manualmente y muestra "Acceso autorizado"', (tester) async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/visitor-qr/abc123/validate');
      return http.Response('{"valido": true, "motivo": null, "property_id": "p1"}', 200);
    });

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('codigo_field')), 'abc123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(find.text('Acceso autorizado.'), findsOneWidget);
  });

  testWidgets('muestra el motivo cuando el código ya fue usado', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"valido": false, "motivo": "ya_usado", "property_id": null}', 200));

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('codigo_field')), 'abc123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(find.text('Este código ya fue usado.'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si la validación falla', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No autorizado"}', 401));

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('codigo_field')), 'abc123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(find.text('No autorizado'), findsOneWidget);
  });

  testWidgets('no valida un código vacío', (tester) async {
    var llamadas = 0;
    final mockClient = MockClient((request) async {
      llamadas++;
      return http.Response('{"valido": true, "motivo": null, "property_id": null}', 200);
    });

    await pumpPantalla(tester, mockClient);

    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(llamadas, 0);
  });
}
