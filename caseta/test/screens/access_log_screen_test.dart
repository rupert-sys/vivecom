import 'package:app_caseta/db/app_database.dart';
import 'package:app_caseta/screens/access_log_screen.dart';
import 'package:app_caseta/services/access_log_service.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/property_service.dart';
import 'package:app_caseta/services/sync_service.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixturePropiedades = '[{"id": "p1", "identificador": "Casa 1", "referencia_pago": "0001", "saldo_a_favor": 0.0}]';
const _fixtureAbiertos = '''
[{"id": "a1", "property_id": "p1", "tipo": "visitante", "hora_entrada": "2026-10-01T10:00:00", "hora_salida": null, "placas": []}]
''';

void main() {
  late AppDatabase db;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  Future<void> pumpPantalla(WidgetTester tester, http.Client client) async {
    final api = ApiClient(client: client);
    // El formulario creció (nombre, acompañantes, identificación...) y un ListView
    // solo construye lo visible: una pantalla alta permite ver todas las secciones.
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AccessLogScreen(
            token: 'un-token',
            db: db,
            propertyService: PropertyService(api: api),
            accessLogService: AccessLogService(api: api),
            syncService: SyncService(db: db, obtenerToken: () => 'un-token', api: api),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  // flutter_test desmonta automáticamente el árbol de widgets AL FINAL de
  // cada testWidgets, antes de que corra cualquier tearDown()/addTearDown()
  // — para entonces ya es tarde para que un tearDown normal evite el bug.
  // Cuando el StreamBuilder de la cola local (drift) se cancela en ese
  // desmontaje automático, drift programa un Timer(Duration.zero) para
  // esperar por si alguien más se suscribe enseguida (ver el comentario en
  // stream_queries.dart: "please call and await Database.close() in your
  // Flutter widget tests"). Solo cerrando la base ANTES de que el test
  // termine (fuera de tearDown) marca `_isShuttingDown = true` a tiempo
  // para que ese Timer nunca se programe.
  void testConAcceso(String descripcion, Future<void> Function(WidgetTester tester) cuerpo) {
    testWidgets(descripcion, (tester) async {
      try {
        await cuerpo(tester);
      } finally {
        await db.close();
      }
    });
  }

  testConAcceso('registrar entrada encola localmente y aparece en la cola con estado pendiente', (tester) async {
    // El POST de sincronización se dispara sin esperarlo (fire-and-forget) en
    // cuanto se encola — se le hace fallar con un 500 a propósito para que el
    // registro se quede en "pending" de forma determinística y la prueba no
    // dependa de si el round-trip mockeado alcanza a resolver antes del assert.
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log' && request.method == 'GET') return http.Response('[]', 200);
      return http.Response('{"detail": "Error de servidor"}', 500);
    });

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('nombre_field')), 'Juan Pérez');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrar entrada'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Visitante · Juan Pérez ·'), findsOneWidget);
    expect(find.text('Pendiente'), findsOneWidget);
  });

  testConAcceso('lista los accesos abiertos con botón de salida', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log' && request.method == 'GET') return http.Response(_fixtureAbiertos, 200);
      return http.Response('{}', 200);
    });

    await pumpPantalla(tester, mockClient);

    expect(find.text('Salida'), findsOneWidget);
  });

  testConAcceso('registrar salida llama al servicio y refresca la lista', (tester) async {
    var salidaLlamada = false;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log/a1/exit') {
        salidaLlamada = true;
        return http.Response('{"id": "a1", "property_id": "p1", "tipo": "visitante", "hora_entrada": "2026-10-01T10:00:00", "hora_salida": "2026-10-01T11:00:00", "placas": []}', 200);
      }
      if (request.url.path == '/access-log' && request.method == 'GET') {
        return http.Response(salidaLlamada ? '[]' : _fixtureAbiertos, 200);
      }
      return http.Response('{}', 200);
    });

    await pumpPantalla(tester, mockClient);

    await tester.tap(find.text('Salida'));
    await tester.pumpAndSettle();

    expect(salidaLlamada, isTrue);
    expect(find.text('No hay accesos abiertos.'), findsOneWidget);
  });

  testConAcceso('muestra un mensaje si no se pueden cargar los accesos abiertos (sin conexión)', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log' && request.method == 'GET') return http.Response('{"detail": "Sin conexión"}', 503);
      return http.Response('{}', 200);
    });

    await pumpPantalla(tester, mockClient);

    expect(find.text('Sin conexión'), findsOneWidget);
  });

  testConAcceso('un visitante o proveedor sin nombre no se registra (reglamento Art. 17 V.1)', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrar entrada'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('error_formulario')), findsOneWidget);
    expect(find.text('Sin registros en cola.'), findsOneWidget);
  });

  testConAcceso('un residente entra sin que se le pida nombre, acompañantes ni identificación', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.method == 'GET') return http.Response('[]', 200);
      return http.Response('{"detail": "x"}', 500);
    });

    await pumpPantalla(tester, mockClient);
    await tester.tap(find.byKey(const Key('tipo_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Residente').last);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('nombre_field')), findsNothing);
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrar entrada'));
    await tester.pumpAndSettle();
    expect(find.text('Pendiente'), findsOneWidget);
  });

  testConAcceso('guarda nombre, acompañantes, identificación y quién autorizó en la cola local', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.method == 'GET') return http.Response('[]', 200);
      return http.Response('{"detail": "x"}', 500);
    });

    await pumpPantalla(tester, mockClient);
    await tester.enterText(find.byKey(const Key('nombre_field')), 'Ana López');
    await tester.enterText(find.byKey(const Key('identificacion_field')), 'INE 1234');
    await tester.tap(find.byKey(const Key('acompanantes_mas')));
    await tester.tap(find.byKey(const Key('acompanantes_mas')));
    await tester.pump();
    expect(find.text('2'), findsOneWidget);
    await tester.tap(find.byKey(const Key('autorizacion_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Le llamé al residente').last);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrar entrada'));
    await tester.pumpAndSettle();

    final fila = (await db.select(db.pendingAccessLogs).get()).single;
    expect(fila.nombreVisitante, 'Ana López');
    expect(fila.acompanantes, 2);
    expect(fila.identificacion, 'INE 1234');
    expect(fila.autorizadoPor, 'telefono');
    // el formulario queda limpio para el siguiente
    expect(tester.widget<TextField>(find.byKey(const Key('nombre_field'))).controller!.text, isEmpty);
    expect(find.text('0'), findsOneWidget);
  });

  Future<void> pumpConCajones(WidgetTester tester, {required int ocupados, int excedidos = 0}) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log/estacionamiento-visitas') {
        final ids = List.generate(excedidos, (i) => '"x$i"').join(',');
        return http.Response(
          '{"total_cajones": 7, "ocupados": $ocupados, "libres": ${7 - ocupados}, "horas_maximas": 24, "excedidos": [$ids]}',
          200,
        );
      }
      return http.Response('[]', 200);
    });
    await pumpPantalla(tester, mockClient);
  }

  testConAcceso('muestra los cajones de visitas libres y cuántos vehículos rebasaron el plazo', (tester) async {
    await pumpConCajones(tester, ocupados: 3, excedidos: 1);

    final tarjeta = find.byKey(const Key('estacionamiento_visitas'));
    expect(find.descendant(of: tarjeta, matching: find.text('Cajones de visitas: 4 libres de 7')), findsOneWidget);
    expect(find.descendant(of: tarjeta, matching: find.textContaining('1 vehículo rebasó las 24 h')), findsOneWidget);
    expect(find.textContaining('Llenos'), findsNothing);
  });

  testConAcceso('con los cajones llenos avisa que solo pasa quien tenga lugar propio', (tester) async {
    await pumpConCajones(tester, ocupados: 7);

    expect(find.text('Cajones de visitas: 0 libres de 7'), findsOneWidget);
    expect(find.textContaining('solo pasa si el visitado tiene lugar propio'), findsOneWidget);
  });

  testConAcceso('sin conexión no se muestra el estacionamiento pero se puede registrar', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log/estacionamiento-visitas') return http.Response('{"detail": "x"}', 503);
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);

    expect(find.byKey(const Key('estacionamiento_visitas')), findsNothing);
    expect(find.widgetWithText(ElevatedButton, 'Registrar entrada'), findsOneWidget);
  });

  testConAcceso('un condominio sin cajones de visitas configurados no muestra la tarjeta', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_fixturePropiedades, 200);
      if (request.url.path == '/access-log/estacionamiento-visitas') {
        return http.Response('{"total_cajones": 0, "ocupados": 0, "libres": 0, "horas_maximas": 24, "excedidos": []}', 200);
      }
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);

    expect(find.byKey(const Key('estacionamiento_visitas')), findsNothing);
  });
}
