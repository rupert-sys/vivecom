import 'dart:typed_data';

import 'package:app_residente/screens/payment_history_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/receipt_service.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureConDosPagos = '''
{
  "property_id": "p1",
  "identificador": "Casa 1",
  "saldo_a_favor": 0.0,
  "deuda_total": 0.0,
  "cargos": [],
  "pagos": [
    {"id": "pg1", "monto": 800.0, "estado": "confirmado", "fecha_deteccion": "2026-08-15T10:00:00", "clave_rastreo": "REF-0001"},
    {"id": "pg2", "monto": 800.0, "estado": "pendiente", "fecha_deteccion": "2026-07-15T10:00:00", "clave_rastreo": "REF-0002"}
  ]
}
''';

void main() {
  Future<void> pumpHistorial(
    WidgetTester tester,
    http.Client client, {
    CompartirPdf compartirPdf = compartirPdfReal,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        home: PaymentHistoryScreen(
          propertyId: 'p1',
          token: 'un-token',
          statementService: StatementService(api: ApiClient(client: client)),
          receiptService: ReceiptService(api: ApiClient(client: client)),
          compartirPdf: compartirPdf,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('lista los pagos con su estado y solo muestra el botón de recibo en los confirmados', (tester) async {
    final mockClient = MockClient((request) async => http.Response(_fixtureConDosPagos, 200));

    await pumpHistorial(tester, mockClient);

    expect(find.text('Confirmado · 2026-08-15 · REF-0001'), findsOneWidget);
    expect(find.text('Pendiente · 2026-07-15 · REF-0002'), findsOneWidget);
    expect(find.byKey(const Key('ver_recibo_pg1')), findsOneWidget);
    expect(find.byKey(const Key('ver_recibo_pg2')), findsNothing);
  });

  testWidgets('al tocar "ver recibo" descarga los bytes y los pasa a compartirPdf', (tester) async {
    Uint8List? bytesCompartidos;
    String? nombreCompartido;

    final mockClient = MockClient((request) async {
      if (request.url.path.endsWith('/receipt')) {
        return http.Response.bytes([0x25, 0x50, 0x44, 0x46], 200);
      }
      return http.Response(_fixtureConDosPagos, 200);
    });

    await pumpHistorial(
      tester,
      mockClient,
      compartirPdf: (bytes, filename) async {
        bytesCompartidos = bytes;
        nombreCompartido = filename;
      },
    );

    await tester.tap(find.byKey(const Key('ver_recibo_pg1')));
    await tester.pumpAndSettle();

    expect(bytesCompartidos, [0x25, 0x50, 0x44, 0x46]);
    expect(nombreCompartido, 'recibo-REF-0001.pdf');
  });

  testWidgets('muestra un SnackBar con el error si falla la descarga del recibo', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path.endsWith('/receipt')) {
        return http.Response('{"detail": "Solo hay recibo para pagos confirmados"}', 409);
      }
      return http.Response(_fixtureConDosPagos, 200);
    });

    await pumpHistorial(tester, mockClient);

    await tester.tap(find.byKey(const Key('ver_recibo_pg1')));
    await tester.pumpAndSettle();

    expect(find.text('Solo hay recibo para pagos confirmados'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay pagos', (tester) async {
    final mockClient = MockClient(
      (request) async => http.Response(
        '{"property_id": "p1", "identificador": "Casa 1", "saldo_a_favor": 0.0, "deuda_total": 0.0, "cargos": [], "pagos": []}',
        200,
      ),
    );

    await pumpHistorial(tester, mockClient);

    expect(find.text('Todavía no hay pagos registrados.'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si falla la carga', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No tienes acceso"}', 403));

    await pumpHistorial(tester, mockClient);

    expect(find.text('No tienes acceso'), findsOneWidget);
  });
}
