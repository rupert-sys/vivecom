import 'package:app_caseta/db/app_database.dart';
import 'package:app_caseta/screens/caseta_home_screen.dart';
import 'package:app_caseta/services/access_log_service.dart';
import 'package:app_caseta/services/package_service.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/property_service.dart';
import 'package:app_caseta/services/sync_service.dart';
import 'package:app_caseta/services/visitor_qr_service.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('navega entre Accesos, Paquetes, Incidencias y Códigos QR sin perder cada pantalla', (tester) async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());

    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties' || request.url.path == '/access-log' || request.url.path == '/packages') {
        return http.Response('[]', 200);
      }
      return http.Response('{}', 200);
    });
    final api = ApiClient(client: mockClient);
    var logoutLlamado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: CasetaHomeScreen(
          token: 'un-token',
          db: db,
          propertyService: PropertyService(api: api),
          accessLogService: AccessLogService(api: api),
          visitorQrService: VisitorQrService(api: api),
          packageService: PackageService(api: api),
          syncService: SyncService(db: db, obtenerToken: () => 'un-token', api: api),
          onLogout: () => logoutLlamado = true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // "Registrar entrada" aparece dos veces dentro de AccessLogScreen (el
    // título de la tarjeta y el botón) — se busca el botón específicamente
    // para no ser ambiguo.
    expect(find.widgetWithText(ElevatedButton, 'Registrar entrada'), findsOneWidget);

    await tester.tap(find.text('Paquetes'));
    await tester.pumpAndSettle();
    expect(find.text('Registrar llegada de paquete'), findsOneWidget);

    await tester.tap(find.text('Incidencias'));
    await tester.pumpAndSettle();
    expect(find.text('Reportar incidencia'), findsOneWidget);

    await tester.tap(find.text('Códigos QR'));
    await tester.pumpAndSettle();
    expect(find.text('Escanear QR de visitante'), findsOneWidget);

    await tester.tap(find.text('Accesos'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(ElevatedButton, 'Registrar entrada'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.logout));
    await tester.pumpAndSettle();
    expect(logoutLlamado, isTrue);

    // Ver la nota extensa en access_log_screen_test.dart: db.close() debe
    // correr DENTRO del test (no en tearDown/addTearDown) para que drift
    // marque `_isShuttingDown = true` antes de que flutter_test desmonte el
    // árbol automáticamente al final de cada testWidgets.
    await db.close();
  });
}
