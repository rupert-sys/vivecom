import 'package:app_residente/screens/residente_home_screen.dart';
import 'package:app_residente/services/announcement_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/clabe_service.dart';
import 'package:app_residente/services/expense_service.dart';
import 'package:app_residente/services/fee_service.dart';
import 'package:app_residente/services/property_service.dart';
import 'package:app_residente/services/receipt_service.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('navega entre Estado de cuenta, Pago, Historial, Gastos, Avisos y CLABE sin perder cada pantalla', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) {
        return http.Response(
          '{"property_id": "p1", "identificador": "Casa 1", "saldo_a_favor": 0.0, "deuda_total": 0.0, "cargos": [], "pagos": []}',
          200,
        );
      }
      if (path.endsWith('/clabe')) {
        return http.Response('{"id": "t1", "nombre": "Residencial Las Torres", "clabe_destino": "646180157012345678"}', 200);
      }
      if (path == '/properties/p1') {
        return http.Response('{"id": "p1", "identificador": "Casa 1", "referencia_pago": "0012345", "saldo_a_favor": 0.0}', 200);
      }
      if (path == '/fees') {
        return http.Response('[{"id": "f1", "monto": 800.0, "periodicidad": "mensual", "activa_desde": "2026-01-01"}]', 200);
      }
      if (path == '/expenses') {
        return http.Response(
          '[{"id": "g1", "categoria": "Jardinería", "monto": 1200.0, "comprobante_url": "https://example.com/r.pdf", "fecha": "2026-09-01"}]',
          200,
        );
      }
      if (path == '/announcements') {
        return http.Response(
          '[{"id": "a1", "titulo": "Corte de agua", "contenido": "Texto", "fecha_publicacion": "2026-09-16T10:00:00", "leido": false}]',
          200,
        );
      }
      return http.Response('not found', 404);
    });

    await tester.pumpWidget(
      MaterialApp(
        home: ResidenteHomeScreen(
          propertyId: 'p1',
          token: 'un-token',
          statementService: StatementService(api: ApiClient(client: mockClient)),
          clabeService: ClabeService(api: ApiClient(client: mockClient)),
          propertyService: PropertyService(api: ApiClient(client: mockClient)),
          feeService: FeeService(api: ApiClient(client: mockClient)),
          receiptService: ReceiptService(api: ApiClient(client: mockClient)),
          expenseService: ExpenseService(api: ApiClient(client: mockClient)),
          announcementService: AnnouncementService(api: ApiClient(client: mockClient)),
          onLogout: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Casa 1'), findsOneWidget);
    expect(find.text('646180157012345678'), findsNothing);

    await tester.tap(find.text('Pago'));
    await tester.pumpAndSettle();

    expect(find.text('Transfiere \$800.00'), findsOneWidget);

    await tester.tap(find.text('Historial'));
    await tester.pumpAndSettle();

    expect(find.text('Todavía no hay pagos registrados.'), findsOneWidget);

    await tester.tap(find.text('Gastos'));
    await tester.pumpAndSettle();

    expect(find.text('Jardinería'), findsOneWidget);

    await tester.tap(find.text('Avisos'));
    await tester.pumpAndSettle();

    expect(find.text('Corte de agua'), findsOneWidget);

    await tester.tap(find.text('CLABE'));
    await tester.pumpAndSettle();

    expect(find.text('646180157012345678'), findsOneWidget);

    await tester.tap(find.text('Estado de cuenta'));
    await tester.pumpAndSettle();

    expect(find.text('Casa 1'), findsOneWidget);
  });
}
