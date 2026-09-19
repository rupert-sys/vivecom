import 'package:app_residente/screens/payment_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/clabe_service.dart';
import 'package:app_residente/services/fee_service.dart';
import 'package:app_residente/services/payment_proof_service.dart';
import 'package:app_residente/services/property_service.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureClabe = '{"id": "t1", "nombre": "Residencial Las Torres", "clabe_destino": "646180157012345678"}';
const _fixturePropiedad = '{"id": "p1", "identificador": "Casa 1", "referencia_pago": "0012345", "saldo_a_favor": 0.0}';

http.Response _statementResponse({double deudaTotal = 0.0, List<String> pagosJson = const []}) {
  return http.Response(
    '{"property_id": "p1", "identificador": "Casa 1", "saldo_a_favor": 0.0, "deuda_total": $deudaTotal, '
    '"cargos": [], "pagos": [${pagosJson.join(',')}]}',
    200,
  );
}

const _pagoConfirmado =
    '{"id": "pg1", "monto": 800.0, "estado": "confirmado", "fecha_deteccion": "2026-08-15T10:00:00", "clave_rastreo": "REF-0001"}';

http.Response _cuotaMensualResponse({double monto = 800.0}) =>
    http.Response('[{"id": "f1", "monto": $monto, "periodicidad": "mensual", "activa_desde": "2026-01-01"}]', 200);

Future<void> _pumpPayment(
  WidgetTester tester,
  http.Client client, {
  double deudaTotal = 0.0,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: PaymentScreen(
        propertyId: 'p1',
        token: 'un-token',
        statementService: StatementService(api: ApiClient(client: client)),
        propertyService: PropertyService(api: ApiClient(client: client)),
        feeService: FeeService(api: ApiClient(client: client)),
        clabeService: ClabeService(api: ApiClient(client: client)),
        proofService: PaymentProofService(api: ApiClient(client: client)),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('muestra el pago más reciente y el calculador de pago anticipado', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) {
        return _statementResponse(pagosJson: [_pagoConfirmado]);
      }
      if (path.endsWith('/clabe')) return http.Response(_fixtureClabe, 200);
      if (path == '/properties/p1') return http.Response(_fixturePropiedad, 200);
      if (path == '/fees') return _cuotaMensualResponse();
      return http.Response('not found', 404);
    });

    await _pumpPayment(tester, mockClient);

    expect(find.text('\$800.00'), findsOneWidget);
    expect(find.text('Confirmado'), findsOneWidget);
    expect(find.text('Referencia: REF-0001'), findsOneWidget);

    // Con deuda 0 y 1 mes seleccionado por defecto: transfiere 1 × 800.
    expect(find.text('Transfiere \$800.00'), findsOneWidget);
    expect(find.text('CLABE: 646180157012345678'), findsOneWidget);
    expect(find.text('Referencia: 0012345'), findsOneWidget);
  });

  testWidgets('el total incluye la deuda actual más los meses seleccionados', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) return _statementResponse(deudaTotal: 200.0);
      if (path.endsWith('/clabe')) return http.Response(_fixtureClabe, 200);
      if (path == '/properties/p1') return http.Response(_fixturePropiedad, 200);
      if (path == '/fees') return _cuotaMensualResponse(monto: 800.0);
      return http.Response('not found', 404);
    });

    await _pumpPayment(tester, mockClient, deudaTotal: 200.0);

    // 1 mes por defecto: 200 (deuda) + 1×800 = 1000.
    expect(find.text('Transfiere \$1000.00'), findsOneWidget);
    expect(find.text('Deuda actual: \$200.00'), findsOneWidget);

    await tester.tap(find.byKey(const Key('meses_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('3 meses').last);
    await tester.pumpAndSettle();

    // 200 + 3×800 = 2600.
    expect(find.text('Transfiere \$2600.00'), findsOneWidget);
  });

  testWidgets('muestra un aviso en vez del calculador cuando la cuota vigente es bimestral', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) return _statementResponse();
      if (path.endsWith('/clabe')) return http.Response(_fixtureClabe, 200);
      if (path == '/properties/p1') return http.Response(_fixturePropiedad, 200);
      if (path == '/fees') {
        return http.Response('[{"id": "f1", "monto": 1500.0, "periodicidad": "bimestral", "activa_desde": "2026-01-01"}]', 200);
      }
      return http.Response('not found', 404);
    });

    await _pumpPayment(tester, mockClient);

    expect(find.byKey(const Key('meses_dropdown')), findsNothing);
    expect(find.textContaining('no está disponible'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay pagos registrados', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) return _statementResponse();
      if (path.endsWith('/clabe')) return http.Response(_fixtureClabe, 200);
      if (path == '/properties/p1') return http.Response(_fixturePropiedad, 200);
      if (path == '/fees') return _cuotaMensualResponse();
      return http.Response('not found', 404);
    });

    await _pumpPayment(tester, mockClient);

    expect(find.text('Todavía no hay pagos registrados.'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si falla la carga', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No tienes acceso"}', 403));

    await _pumpPayment(tester, mockClient);

    expect(find.text('No tienes acceso'), findsOneWidget);
  });

  testWidgets('ofrece "Ya pagué" y abre la pantalla para adjuntar el comprobante', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) return _statementResponse();
      if (path.endsWith('/clabe')) return http.Response(_fixtureClabe, 200);
      if (path == '/properties/p1') return http.Response(_fixturePropiedad, 200);
      if (path == '/fees') return _cuotaMensualResponse();
      if (path == '/payment-proofs') return http.Response('[]', 200);
      return http.Response('not found', 404);
    });

    await _pumpPayment(tester, mockClient);
    await tester.tap(find.byKey(const Key('adjuntar_comprobante')));
    await tester.pumpAndSettle();

    expect(find.text('Comprobantes de pago'), findsOneWidget);
    expect(find.text('Todavía no has enviado comprobantes.'), findsOneWidget);
  });
}
