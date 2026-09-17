import 'package:app_caseta/db/app_database.dart';
import 'package:app_caseta/screens/incident_screen.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/sync_service.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  late AppDatabase db;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  Future<void> pumpPantalla(WidgetTester tester, http.Client client) async {
    final api = ApiClient(client: client);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: IncidentScreen(db: db, syncService: SyncService(db: db, obtenerToken: () => 'un-token', api: api))),
      ),
    );
    await tester.pumpAndSettle();
  }

  // Ver la nota extensa en access_log_screen_test.dart: db.close() debe
  // correr DENTRO del test (no en tearDown) para que drift marque
  // `_isShuttingDown = true` antes de que flutter_test desmonte el árbol
  // automáticamente al final de cada testWidgets.
  void testConIncidencia(String descripcion, Future<void> Function(WidgetTester tester) cuerpo) {
    testWidgets(descripcion, (tester) async {
      try {
        await cuerpo(tester);
      } finally {
        await db.close();
      }
    });
  }

  testConIncidencia('reportar una incidencia la encola localmente con estado pendiente', (tester) async {
    // Mismo motivo que en access_log_screen_test: el sync fire-and-forget se
    // hace fallar a propósito (500) para que el assert de "Pendiente" no
    // dependa del timing del round-trip mockeado.
    final mockClient = MockClient((request) async => http.Response('{"detail": "Error de servidor"}', 500));

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('descripcion_field')), 'Fuga de agua en estacionamiento');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Reportar'));
    await tester.pumpAndSettle();

    expect(find.text('Fuga de agua en estacionamiento'), findsOneWidget);
    expect(find.text('Pendiente'), findsOneWidget);
  });

  testConIncidencia('no reporta si la descripción está vacía', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{}', 201));
    await pumpPantalla(tester, mockClient);

    await tester.tap(find.widgetWithText(ElevatedButton, 'Reportar'));
    await tester.pumpAndSettle();

    expect(find.text('Sin incidencias en cola.'), findsOneWidget);
  });

  testConIncidencia('muestra un mensaje cuando no hay incidencias en cola', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{}', 201));
    await pumpPantalla(tester, mockClient);

    expect(find.text('Sin incidencias en cola.'), findsOneWidget);
  });
}
