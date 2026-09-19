import 'package:app_caseta/db/app_database.dart';
import 'package:app_caseta/screens/incident_screen.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/property_service.dart';
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
    tester.view.physicalSize = const Size(800, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: IncidentScreen(
            token: 'un-token',
            db: db,
            propertyService: PropertyService(api: api),
            syncService: SyncService(db: db, obtenerToken: () => 'un-token', api: api),
          ),
        ),
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

  const fixturePropiedades = '[{"id": "p1", "identificador": "Casa 1"}, {"id": "p2", "identificador": "Casa 2"}]';

  MockClient servidorConCasas() => MockClient((request) async {
    if (request.url.path == '/properties') return http.Response(fixturePropiedades, 200);
    return http.Response('{"detail": "Error de servidor"}', 500);
  });

  testConIncidencia('sin elegir tipo la incidencia es de seguridad', (tester) async {
    await pumpPantalla(tester, servidorConCasas());

    await tester.enterText(find.byKey(const Key('descripcion_field')), 'Persona extraña en la puerta');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Reportar'));
    await tester.pumpAndSettle();

    final fila = (await db.select(db.pendingIncidents).get()).single;
    expect(fila.tipo, 'seguridad');
    expect(fila.propertyId, isNull);
    expect(fila.personaInvolucrada, isNull);
  });

  testConIncidencia('reporta una falla de mantenimiento con la casa y la persona involucradas', (tester) async {
    await pumpPantalla(tester, servidorConCasas());

    await tester.tap(find.text('Mantenimiento'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('descripcion_field')), 'Luminaria fundida frente a la casa');
    await tester.tap(find.byKey(const Key('incidente_vivienda_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Casa 2').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('persona_field')), 'Vecino de la Casa 2');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Reportar'));
    await tester.pumpAndSettle();

    final fila = (await db.select(db.pendingIncidents).get()).single;
    expect(fila.tipo, 'mantenimiento');
    expect(fila.propertyId, 'p2');
    expect(fila.personaInvolucrada, 'Vecino de la Casa 2');
    expect(find.textContaining('Mantenimiento ·'), findsOneWidget); // la cola dice de qué tipo es
  });

  testConIncidencia('tras reportar, el formulario vuelve a seguridad y sin casa', (tester) async {
    await pumpPantalla(tester, servidorConCasas());

    await tester.tap(find.text('Mantenimiento'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('descripcion_field')), 'Portón atorado');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Reportar'));
    await tester.pumpAndSettle();

    final segmentos = tester.widget<SegmentedButton<String>>(find.byKey(const Key('tipo_incidencia')));
    expect(segmentos.selected, {'seguridad'});
  });

  testConIncidencia('sin conexión se puede reportar aunque no cargue la lista de casas', (tester) async {
    await pumpPantalla(tester, MockClient((request) async => throw http.ClientException('sin red')));

    await tester.enterText(find.byKey(const Key('descripcion_field')), 'Ruido excesivo');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Reportar'));
    await tester.pumpAndSettle();

    expect(await db.select(db.pendingIncidents).get(), hasLength(1));
  });
}
