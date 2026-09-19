import 'dart:convert';

import 'package:app_caseta/screens/qr_scan_screen.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/property_service.dart';
import 'package:app_caseta/services/visitor_qr_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  Future<void> pumpPantalla(WidgetTester tester, http.Client client) async {
    final api = ApiClient(client: client);
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QrScanScreen(
            token: 'un-token',
            visitorQrService: VisitorQrService(api: api),
            propertyService: PropertyService(api: api),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  // El Simulador de iOS/entorno de pruebas no tiene cámara real: mobile_scanner
  // falla al inicializar su canal de plataforma y cae en errorBuilder — así que
  // estas pruebas cubren el flujo de código manual, que es el único
  // verificable sin hardware real (y el respaldo real para un guardia si la
  // cámara falla).
  testWidgets('valida un código manualmente y muestra "Acceso autorizado"', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response('[]', 200);
      expect(request.url.toString(), 'http://localhost:8000/visitor-qr/abc123/validate');
      return http.Response('{"valido": true, "motivo": null, "property_id": "p1"}', 200);
    });

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('codigo_field')), 'abc123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(find.text('Acceso autorizado.'), findsOneWidget);
  });

  testWidgets('muestra el motivo cuando el código ya fue usado', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"valido": false, "motivo": "ya_usado", "property_id": null}', 200));

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('codigo_field')), 'abc123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(find.text('Este código ya fue usado.'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si la validación falla', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "No autorizado"}', 401));

    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('codigo_field')), 'abc123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(find.text('No autorizado'), findsOneWidget);
  });

  testWidgets('no valida un código vacío', (tester) async {
    var llamadas = 0;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response('[]', 200);
      llamadas++;
      return http.Response('{"valido": true, "motivo": null, "property_id": null}', 200);
    });

    await pumpPantalla(tester, mockClient);

    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();

    expect(llamadas, 0);
  });

  const propiedades = '[{"id": "p1", "identificador": "Casa 1"}, {"id": "p4", "identificador": "Casa 4"}]';

  Future<void> validar(WidgetTester tester, String codigo) async {
    await tester.enterText(find.byKey(const Key('codigo_field')), codigo);
    await tester.tap(find.widgetWithText(ElevatedButton, 'Validar'));
    await tester.pumpAndSettle();
  }

  testWidgets('al validar el código de una visita dice a qué vivienda va', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      return http.Response(
        '{"valido": true, "motivo": null, "property_id": "p4", "tipo": "visitante", "descripcion": null, "vivienda": "Casa 4"}',
        200,
      );
    });
    await pumpPantalla(tester, mockClient);

    await validar(tester, 'abc');

    expect(find.text('Acceso autorizado.'), findsOneWidget);
    expect(find.text('Va a: Casa 4'), findsOneWidget);
    expect(find.textContaining('Proveedor:'), findsNothing);
  });

  testWidgets('al validar el código de un proveedor dice quién es y a dónde va', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      return http.Response(
        '{"valido": true, "motivo": null, "property_id": "p4", "tipo": "proveedor", "descripcion": "Plomería López", "vivienda": "Casa 4"}',
        200,
      );
    });
    await pumpPantalla(tester, mockClient);

    await validar(tester, 'abc');

    expect(find.text('Proveedor: Plomería López'), findsOneWidget);
    expect(find.text('Va a: Casa 4'), findsOneWidget);
  });

  testWidgets('un proveedor del condominio en general se muestra sin vivienda', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      return http.Response(
        '{"valido": true, "motivo": null, "property_id": null, "tipo": "proveedor", "descripcion": "Jardinería", "vivienda": null}',
        200,
      );
    });
    await pumpPantalla(tester, mockClient);

    await validar(tester, 'abc');

    expect(find.text('Servicio al condominio en general'), findsWidgets);
  });

  testWidgets('el guardia emite un código para un proveedor de una vivienda y ve su QR', (tester) async {
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      expect(request.url.path, '/visitor-qr/provider');
      return http.Response(
        '{"id": "q1", "property_id": "p4", "codigo": "prov-123", "usado": false, "fecha_generado": "2026-09-18T10:00:00", '
        '"fecha_usado": null, "tipo": "proveedor", "descripcion": "Plomería López"}',
        201,
      );
    });
    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('proveedor_descripcion_field')), 'Plomería López');
    await tester.tap(find.byKey(const Key('proveedor_vivienda_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Casa 4').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Emitir código'));
    await tester.pumpAndSettle();

    expect(cuerpo, {'descripcion': 'Plomería López', 'property_id': 'p4'});
    expect(find.byKey(const Key('qr_prov-123')), findsOneWidget);
    expect(find.byKey(const Key('codigo_proveedor')), findsOneWidget);
    expect(find.text('Plomería López'), findsWidgets);
  });

  testWidgets('un proveedor sin vivienda se emite sin property_id', (tester) async {
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(
        '{"id": "q1", "property_id": null, "codigo": "prov-9", "usado": false, "fecha_generado": "2026-09-18T10:00:00", '
        '"fecha_usado": null, "tipo": "proveedor", "descripcion": "Jardinería"}',
        201,
      );
    });
    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('proveedor_descripcion_field')), 'Jardinería');
    await tester.tap(find.text('Emitir código'));
    await tester.pumpAndSettle();

    expect(cuerpo, {'descripcion': 'Jardinería'});
    expect(find.byKey(const Key('qr_prov-9')), findsOneWidget);
  });

  testWidgets('no emite un código de proveedor sin anotar quién es', (tester) async {
    var emisiones = 0;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      emisiones++;
      return http.Response('{}', 201);
    });
    await pumpPantalla(tester, mockClient);

    await tester.tap(find.text('Emitir código'));
    await tester.pumpAndSettle();

    expect(emisiones, 0);
    expect(find.textContaining('Anota quién es el proveedor'), findsOneWidget);
  });

  testWidgets('si no hay conexión al emitir, muestra el error y no un QR', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/properties') return http.Response(propiedades, 200);
      return http.Response('{"detail": "Vivienda no encontrada"}', 404);
    });
    await pumpPantalla(tester, mockClient);

    await tester.enterText(find.byKey(const Key('proveedor_descripcion_field')), 'Mensajería');
    await tester.tap(find.text('Emitir código'));
    await tester.pumpAndSettle();

    expect(find.text('Vivienda no encontrada'), findsOneWidget);
    expect(find.byKey(const Key('qr_proveedor')), findsNothing);
  });
}
