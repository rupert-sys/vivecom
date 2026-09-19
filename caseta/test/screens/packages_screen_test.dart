import 'package:app_caseta/db/app_database.dart';
import 'package:app_caseta/screens/packages_screen.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/package_service.dart';
import 'package:app_caseta/services/property_service.dart';
import 'package:app_caseta/services/sync_service.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _propiedades = '[{"id": "p1", "identificador": "Casa 1"}, {"id": "p2", "identificador": "Casa 2"}]';
const _paqueteEnCaseta = '[{"id": "k1", "property_id": "p2", "fecha_llegada": "2026-09-18T15:30:00", "fecha_recogido": null}]';

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
          body: PackagesScreen(
            token: 'un-token',
            db: db,
            propertyService: PropertyService(api: api),
            packageService: PackageService(api: api),
            syncService: SyncService(db: db, obtenerToken: () => 'un-token', api: api),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  // Ver la nota extensa en access_log_screen_test.dart sobre cerrar la base
  // DENTRO del test.
  void testConPaquetes(String descripcion, Future<void> Function(WidgetTester tester) cuerpo) {
    testWidgets(descripcion, (tester) async {
      try {
        await cuerpo(tester);
      } finally {
        await db.close();
      }
    });
  }

  Future<void> elegirVivienda(WidgetTester tester, String nombre) async {
    await tester.tap(find.byKey(const Key('paquete_vivienda_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text(nombre).last);
    await tester.pumpAndSettle();
  }

  testConPaquetes('muestra los paquetes que siguen en la caseta con la vivienda y la hora', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      return http.Response(_paqueteEnCaseta, 200);
    });

    await pumpPantalla(tester, mockClient);

    final paquete = find.byKey(const Key('paquete_k1'));
    expect(find.descendant(of: paquete, matching: find.text('Casa 2')), findsOneWidget);
    expect(find.descendant(of: paquete, matching: find.textContaining('Llegó a las')), findsOneWidget);
    expect(find.text('Entregado'), findsOneWidget);
  });

  testConPaquetes('sin paquetes muestra el mensaje vacío', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);

    expect(find.text('No hay paquetes esperando a su residente.'), findsOneWidget);
    expect(find.text('Sin paquetes en cola.'), findsOneWidget);
  });

  testConPaquetes('registrar la llegada la encola con la vivienda y se sincroniza para avisar al residente', (tester) async {
    final rutas = <String>[];
    final mockClient = MockClient((request) async {
      rutas.add('${request.method} ${request.url.path}');
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      if (request.method == 'POST' && request.url.path == '/packages') return http.Response('{"id": "rk1"}', 201);
      if (request.url.path == '/packages/send-notifications') return http.Response('{}', 200);
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await elegirVivienda(tester, 'Casa 1');
    await tester.tap(find.text('Registrar paquete'));
    await tester.pumpAndSettle();

    final fila = await db.select(db.pendingPackages).getSingle();
    expect(fila.propertyId, 'p1');
    expect(fila.syncStatus, 'synced');
    expect(rutas, containsAllInOrder(['POST /packages', 'POST /packages/send-notifications']));
    expect(find.text('Sincronizado'), findsOneWidget);
  });

  testConPaquetes('sin conexión el paquete queda pendiente en la cola pero se registró', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      if (request.method == 'POST') return http.Response('{"detail": "sin red"}', 503);
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await elegirVivienda(tester, 'Casa 2');
    await tester.tap(find.text('Registrar paquete'));
    await tester.pumpAndSettle();

    expect(find.text('Pendiente'), findsOneWidget);
    expect(find.textContaining('Casa 2 ·'), findsOneWidget);
  });

  testConPaquetes('no registra un paquete sin elegir la vivienda', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.tap(find.text('Registrar paquete'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('error_paquete')), findsOneWidget);
    expect(await db.select(db.pendingPackages).get(), isEmpty);
  });

  testConPaquetes('entregar un paquete llama al servicio y lo quita de la lista', (tester) async {
    var entregado = false;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      if (request.url.path == '/packages/k1/pickup') {
        entregado = true;
        return http.Response('{"id": "k1"}', 200);
      }
      return http.Response(entregado ? '[]' : _paqueteEnCaseta, 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.tap(find.text('Entregado'));
    await tester.pumpAndSettle();

    expect(entregado, isTrue);
    expect(find.text('No hay paquetes esperando a su residente.'), findsOneWidget);
  });

  testConPaquetes('si la entrega falla muestra el motivo y el paquete sigue en la lista', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      if (request.url.path == '/packages/k1/pickup') return http.Response('{"detail": "Este paquete ya fue recogido"}', 409);
      return http.Response(_paqueteEnCaseta, 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.tap(find.text('Entregado'));
    await tester.pumpAndSettle();

    expect(find.text('Este paquete ya fue recogido'), findsOneWidget);
    expect(find.byKey(const Key('paquete_k1')), findsOneWidget);
  });

  testConPaquetes('sin conexión la lista de la caseta avisa y no bloquea registrar', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(_propiedades, 200);
      return http.Response('{"detail": "Sin conexión"}', 503);
    });

    await pumpPantalla(tester, mockClient);

    expect(find.text('Sin conexión'), findsOneWidget);
    expect(find.text('Registrar paquete'), findsOneWidget);
  });
}
