import 'package:app_residente/screens/dashboard_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/cash_movement_service.dart';
import 'package:app_residente/services/expense_service.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  Future<void> pumpDashboard(WidgetTester tester, http.Client client) async {
    final api = ApiClient(client: client);
    await tester.pumpWidget(
      MaterialApp(
        home: DashboardScreen(
          propertyId: 'p1',
          token: 'un-token',
          statementService: StatementService(api: api),
          expenseService: ExpenseService(api: api),
          cashMovementService: CashMovementService(api: api),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('muestra el estado de cuenta propio, el resumen del condominio y la caja', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) {
        return http.Response(
          '{"property_id": "p1", "identificador": "Casa 1", "saldo_a_favor": 500.0, "deuda_total": 0.0, "cargos": [], "pagos": []}',
          200,
        );
      }
      if (path == '/expenses/summary') {
        return http.Response(
          '{"ingresos": 5000.0, "gastos": 1200.0, "saldo": 3800.0, "por_cobrar": 0.0, "gastos_por_categoria": []}',
          200,
        );
      }
      if (path == '/cash-movements/balance') {
        return http.Response('{"chica": 1500.0, "grande": 48000.0}', 200);
      }
      return http.Response('not found', 404);
    });

    await pumpDashboard(tester, mockClient);

    expect(find.text('Tu vivienda'), findsOneWidget);
    expect(find.text('\$500.00'), findsOneWidget); // saldo a favor
    expect(find.text('El condominio'), findsOneWidget);
    expect(find.text('\$5000.00'), findsOneWidget); // ingresos
    expect(find.text('\$1200.00'), findsOneWidget); // egresos
    expect(find.text('Caja chica y grande'), findsOneWidget);
    expect(find.text('\$1500.00'), findsOneWidget); // caja chica
    expect(find.text('\$48000.00'), findsOneWidget); // caja grande
  });

  testWidgets('si falla el resumen del condominio o la caja, el estado de cuenta propio sigue visible', (tester) async {
    final mockClient = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/statement')) {
        return http.Response(
          '{"property_id": "p1", "identificador": "Casa 1", "saldo_a_favor": 0.0, "deuda_total": 300.0, "cargos": [], "pagos": []}',
          200,
        );
      }
      return http.Response('not found', 404);
    });

    await pumpDashboard(tester, mockClient);

    expect(find.text('Tu vivienda'), findsOneWidget);
    expect(find.text('\$300.00'), findsOneWidget); // adeudo
    expect(find.text('El condominio'), findsNothing);
    expect(find.text('Caja chica y grande'), findsNothing);
  });

  testWidgets('muestra el error del backend si falla el estado de cuenta propio', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "No tienes acceso a esta vivienda"}', 403);
    });

    await pumpDashboard(tester, mockClient);

    expect(find.text('No tienes acceso a esta vivienda'), findsOneWidget);
  });
}
