import 'package:app_residente/screens/statement_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureEstadoDeCuenta = '''
{
  "property_id": "p1",
  "identificador": "Casa 1",
  "saldo_a_favor": 150.0,
  "deuda_total": 500.0,
  "cargos": [
    {
      "id": "c1",
      "periodo": "2026-09-01",
      "monto_base": 500.0,
      "recargo_aplicado": 0.0,
      "estado": "vencido"
    }
  ],
  "pagos": [
    {
      "id": "pg1",
      "monto": 650.0,
      "estado": "confirmado",
      "fecha_deteccion": "2026-08-15T10:00:00",
      "clave_rastreo": "REF-0001"
    }
  ]
}
''';

void main() {
  Future<void> pumpStatement(WidgetTester tester, StatementService service, {VoidCallback? onLogout}) async {
    await tester.pumpWidget(
      MaterialApp(
        home: StatementScreen(
          propertyId: 'p1',
          token: 'un-token',
          statementService: service,
          onLogout: onLogout ?? () {},
        ),
      ),
    );
  }

  testWidgets('muestra identificador, deuda total, saldo a favor, cargos y pagos', (tester) async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/properties/p1/statement');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(_fixtureEstadoDeCuenta, 200);
    });
    final service = StatementService(api: ApiClient(client: mockClient));

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    expect(find.text('Casa 1'), findsOneWidget);
    expect(find.text('Deuda total: \$500.00'), findsOneWidget);
    expect(find.text('Saldo a favor: \$150.00'), findsOneWidget);
    expect(find.text('2026-09'), findsOneWidget);
    expect(find.text('Vencido'), findsOneWidget);
    expect(find.text('\$650.00'), findsOneWidget);
    expect(find.textContaining('Confirmado'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay cargos ni pagos', (tester) async {
    final vacio = '''
      {
        "property_id": "p1",
        "identificador": "Casa 2",
        "saldo_a_favor": 0.0,
        "deuda_total": 0.0,
        "cargos": [],
        "pagos": []
      }
    ''';
    final mockClient = MockClient((request) async => http.Response(vacio, 200));
    final service = StatementService(api: ApiClient(client: mockClient));

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    expect(find.text('Todavía no hay cargos.'), findsOneWidget);
    expect(find.text('Todavía no hay pagos registrados.'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si falla la carga', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No tienes acceso"}', 403));
    final service = StatementService(api: ApiClient(client: mockClient));

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    expect(find.text('No tienes acceso'), findsOneWidget);
  });

  testWidgets('el botón de cerrar sesión llama a onLogout', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureEstadoDeCuenta, 200));
    final service = StatementService(api: ApiClient(client: mockClient));
    var logoutLlamado = false;

    await pumpStatement(tester, service, onLogout: () => logoutLlamado = true);
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.logout));
    await tester.pump();

    expect(logoutLlamado, isTrue);
  });

  testWidgets('una vivienda en mora ve el aviso con lo que el reglamento le restringe', (tester) async {
    final enMora = _fixtureEstadoDeCuenta.replaceFirst(
      '"pagos"',
      '"en_mora": true, "restricciones_por_mora": ["No puedes votar en las votaciones.", "No puedes reservar áreas comunes."], "pagos"',
    );
    final service = StatementService(api: ApiClient(client: MockClient((request) async => http.Response(enMora, 200))));

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    final aviso = find.byKey(const Key('aviso_mora'));
    expect(aviso, findsOneWidget);
    expect(find.descendant(of: aviso, matching: find.text('Tu vivienda tiene cuotas vencidas')), findsOneWidget);
    expect(find.descendant(of: aviso, matching: find.text('• No puedes votar en las votaciones.')), findsOneWidget);
    expect(find.descendant(of: aviso, matching: find.text('• No puedes reservar áreas comunes.')), findsOneWidget);
  });

  testWidgets('una vivienda al corriente no ve el aviso de mora', (tester) async {
    final service = StatementService(
      api: ApiClient(client: MockClient((request) async => http.Response(_fixtureEstadoDeCuenta, 200))),
    );

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('aviso_mora')), findsNothing);
  });

  testWidgets('con un acuerdo de pago vigente lo dice y no hay aviso de mora', (tester) async {
    final conAcuerdo = _fixtureEstadoDeCuenta.replaceFirst('"pagos"', '"en_mora": false, "en_acuerdo": true, "pagos"');
    final service = StatementService(
      api: ApiClient(client: MockClient((request) async => http.Response(conAcuerdo, 200))),
    );

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('aviso_acuerdo')), findsOneWidget);
    expect(find.byKey(const Key('aviso_mora')), findsNothing);
  });

  testWidgets('el aviso de mora ofrece la salida del acuerdo de pago', (tester) async {
    final enMora = _fixtureEstadoDeCuenta.replaceFirst(
      '"pagos"',
      '"en_mora": true, "restricciones_por_mora": ["No puedes votar."], "pagos"',
    );
    final service = StatementService(api: ApiClient(client: MockClient((request) async => http.Response(enMora, 200))));

    await pumpStatement(tester, service);
    await tester.pumpAndSettle();

    expect(find.textContaining('acuerdo de pago en la pestaña Pago'), findsOneWidget);
  });
}
