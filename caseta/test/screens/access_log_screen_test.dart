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

    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrar entrada'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Visitante ·'), findsOneWidget);
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
}
