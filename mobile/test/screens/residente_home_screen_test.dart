import 'package:app_residente/screens/residente_home_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/clabe_service.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('navega entre Estado de cuenta y CLABE sin perder cada pantalla', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path.endsWith('/statement')) {
        return http.Response(
          '{"property_id": "p1", "identificador": "Casa 1", "saldo_a_favor": 0.0, "deuda_total": 0.0, "cargos": [], "pagos": []}',
          200,
        );
      }
      if (request.url.path.endsWith('/clabe')) {
        return http.Response('{"id": "t1", "nombre": "Residencial Las Torres", "clabe_destino": "646180157012345678"}', 200);
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
          onLogout: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Casa 1'), findsOneWidget);
    expect(find.text('646180157012345678'), findsNothing);

    await tester.tap(find.text('CLABE'));
    await tester.pumpAndSettle();

    expect(find.text('646180157012345678'), findsOneWidget);

    await tester.tap(find.text('Estado de cuenta'));
    await tester.pumpAndSettle();

    expect(find.text('Casa 1'), findsOneWidget);
  });
}
