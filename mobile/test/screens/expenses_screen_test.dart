import 'package:app_residente/screens/expenses_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/expense_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureGastos = '''
[
  {"id": "g1", "categoria": "Jardinería", "monto": 1200.0, "comprobante_url": "https://example.com/r1.pdf", "fecha": "2026-09-01"},
  {"id": "g2", "categoria": "Seguridad", "monto": 8000.0, "comprobante_url": "https://example.com/r2.pdf", "fecha": "2026-08-15"}
]
''';

void main() {
  Future<void> pumpGastos(WidgetTester tester, http.Client client, {AbrirUrl? abrirUrl}) async {
    await tester.pumpWidget(
      MaterialApp(
        home: ExpensesScreen(
          token: 'un-token',
          expenseService: ExpenseService(api: ApiClient(client: client)),
          abrirUrl: abrirUrl ?? (url) async {},
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('muestra los gastos con su categoría, monto, fecha y el total', (tester) async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/expenses');
      return http.Response(_fixtureGastos, 200);
    });

    await pumpGastos(tester, mockClient);

    expect(find.text('Jardinería'), findsOneWidget);
    expect(find.text('Seguridad'), findsOneWidget);
    expect(find.text('2026-09-01'), findsOneWidget);
    expect(find.text('2026-08-15'), findsOneWidget);
    expect(find.text('Total: \$9200.00'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay gastos en el periodo', (tester) async {
    final mockClient = MockClient((request) async => http.Response('[]', 200));

    await pumpGastos(tester, mockClient);

    expect(find.text('No hay gastos registrados en este periodo.'), findsOneWidget);
  });

  testWidgets('escribir una categoría y tocar Filtrar manda el filtro al backend', (tester) async {
    String? categoriaRecibida;
    final mockClient = MockClient((request) async {
      categoriaRecibida = request.url.queryParameters['categoria'];
      return http.Response(_fixtureGastos, 200);
    });

    await pumpGastos(tester, mockClient);
    await tester.enterText(find.byKey(const Key('categoria_field')), 'Jardinería');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Filtrar'));
    await tester.pumpAndSettle();

    expect(categoriaRecibida, 'Jardinería');
  });

  testWidgets('tocar "Limpiar filtros" vuelve a cargar sin categoría', (tester) async {
    final categoriasRecibidas = <String?>[];
    final mockClient = MockClient((request) async {
      categoriasRecibidas.add(request.url.queryParameters['categoria']);
      return http.Response(_fixtureGastos, 200);
    });

    await pumpGastos(tester, mockClient);
    await tester.enterText(find.byKey(const Key('categoria_field')), 'Jardinería');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Filtrar'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(TextButton, 'Limpiar filtros'));
    await tester.pumpAndSettle();

    expect(categoriasRecibidas.last, isNull);
    final campo = tester.widget<TextField>(find.byKey(const Key('categoria_field')));
    expect(campo.controller!.text, isEmpty);
  });

  testWidgets('tocar "ver comprobante" llama a abrirUrl con la URL del gasto', (tester) async {
    String? urlAbierta;
    final mockClient = MockClient((request) async => http.Response(_fixtureGastos, 200));

    await pumpGastos(tester, mockClient, abrirUrl: (url) async => urlAbierta = url);

    await tester.tap(find.byKey(const Key('ver_comprobante_g1')));
    await tester.pumpAndSettle();

    expect(urlAbierta, 'https://example.com/r1.pdf');
  });

  testWidgets('muestra el error del backend si falla la carga', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "Error interno"}', 500));

    await pumpGastos(tester, mockClient);

    expect(find.text('Error interno'), findsOneWidget);
  });
}
