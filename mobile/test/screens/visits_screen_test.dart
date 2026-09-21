import 'dart:typed_data';

import 'package:app_residente/screens/visits_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/visit_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _codigoUsado =
    '{"id": "q1", "property_id": "p1", "codigo": "usado-1", "usado": true, "fecha_generado": "2026-09-17T10:00:00", "fecha_usado": "2026-09-17T12:00:00"}';
const _codigoLibre =
    '{"id": "q2", "property_id": "p1", "codigo": "libre-2", "usado": false, "fecha_generado": "2026-09-18T10:00:00", "fecha_usado": null}';

void main() {
  Future<void> pumpVisitas(WidgetTester tester, http.Client client, {CompartirCodigo? compartir}) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: VisitsScreen(
            token: 'un-token',
            visitService: VisitService(api: ApiClient(client: client)),
            compartir: compartir ?? ({required codigo, required imagen, required texto}) async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('sin códigos ni paquetes muestra los mensajes vacíos', (tester) async {
    final mockClient = MockClient((request) async => http.Response('[]', 200));

    await pumpVisitas(tester, mockClient);

    expect(find.text('Todavía no has generado códigos.'), findsOneWidget);
    expect(find.text('No tienes paquetes en la caseta.'), findsOneWidget);
    expect(find.text('Generar código de visita'), findsOneWidget);
    expect(find.byKey(const Key('qr_generado')), findsNothing);
  });

  testWidgets('generar un código muestra su QR y el texto del código, y refresca la lista', (tester) async {
    var generado = false;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/visitor-qr') {
        generado = true;
        return http.Response(_codigoLibre, 201);
      }
      if (request.url.path == '/visitor-qr') return http.Response(generado ? '[$_codigoLibre]' : '[]', 200);
      return http.Response('[]', 200);
    });

    await pumpVisitas(tester, mockClient);
    await tester.tap(find.text('Generar código de visita'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('qr_generado')), findsOneWidget);
    expect(find.byKey(const Key('qr_libre-2')), findsOneWidget);
    expect(find.byKey(const Key('codigo_generado')), findsOneWidget);
    expect(find.text('Generar otro código'), findsOneWidget);
    expect(find.byKey(const Key('codigo_q2')), findsOneWidget);
    expect(find.text('Sin usar'), findsOneWidget);
  });

  testWidgets('la lista distingue códigos usados de sin usar', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/visitor-qr') return http.Response('[$_codigoLibre, $_codigoUsado]', 200);
      return http.Response('[]', 200);
    });

    await pumpVisitas(tester, mockClient);

    expect(find.text('Sin usar'), findsOneWidget);
    expect(find.text('Usado'), findsOneWidget);
  });

  testWidgets('tocar un código sin usar lo vuelve a mostrar como QR', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/visitor-qr') return http.Response('[$_codigoLibre]', 200);
      return http.Response('[]', 200);
    });

    await pumpVisitas(tester, mockClient);
    await tester.tap(find.byKey(const Key('codigo_q2')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('qr_libre-2')), findsOneWidget);
  });

  testWidgets('muestra los paquetes por recoger y los ya recogidos', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/packages/mine') {
        return http.Response(
          '[{"id": "k1", "property_id": "p1", "fecha_llegada": "2026-09-18T09:00:00", "fecha_recogido": null},'
          ' {"id": "k2", "property_id": "p1", "fecha_llegada": "2026-09-10T09:00:00", "fecha_recogido": "2026-09-11T18:00:00"}]',
          200,
        );
      }
      return http.Response('[]', 200);
    });

    await pumpVisitas(tester, mockClient);

    expect(find.text('Por recoger en la caseta'), findsOneWidget);
    expect(find.text('Recogido'), findsOneWidget);
  });

  testWidgets('si fallan los paquetes, igual se pueden generar códigos', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/packages/mine') return http.Response('{"detail": "caído"}', 500);
      return http.Response('[]', 200);
    });

    await pumpVisitas(tester, mockClient);

    expect(find.text('caído'), findsOneWidget);
    expect(find.text('Generar código de visita'), findsOneWidget);
  });

  testWidgets('muestra el error del backend si no se pudo generar el código', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') return http.Response('{"detail": "Esta acción es solo para residentes"}', 400);
      return http.Response('[]', 200);
    });

    await pumpVisitas(tester, mockClient);
    await tester.tap(find.text('Generar código de visita'));
    await tester.pumpAndSettle();

    expect(find.text('Esta acción es solo para residentes'), findsOneWidget);
    expect(find.byKey(const Key('qr_generado')), findsNothing);
  });

  MockClient conUnCodigoLibre() => MockClient((request) async {
    if (request.url.path != '/visitor-qr') return http.Response('[]', 200);
    return request.method == 'POST' ? http.Response(_codigoLibre, 201) : http.Response('[$_codigoLibre]', 200);
  });

  testWidgets('sin un código a la vista no hay nada que compartir', (tester) async {
    await pumpVisitas(tester, MockClient((request) async => http.Response('[]', 200)));

    expect(find.byKey(const Key('compartir_codigo')), findsNothing);
  });

  testWidgets('compartir manda la imagen PNG del QR y un texto con el código', (tester) async {
    String? codigoCompartido, textoCompartido;
    Uint8List? imagenCompartida;
    await pumpVisitas(
      tester,
      conUnCodigoLibre(),
      compartir: ({required codigo, required imagen, required texto}) async {
        codigoCompartido = codigo;
        imagenCompartida = imagen;
        textoCompartido = texto;
      },
    );

    await tester.tap(find.text('Generar código de visita'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('compartir_codigo')));
    await tester.tap(find.byKey(const Key('compartir_codigo')));
    // El PNG se codifica con el motor de imágenes: necesita tiempo real, no el reloj falso de la prueba.
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 500)));
    await tester.pumpAndSettle();

    expect(codigoCompartido, 'libre-2');
    expect(textoCompartido, contains('libre-2'));
    expect(textoCompartido, contains('una sola vez'));
    expect(imagenCompartida!.sublist(0, 8), [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]); // firma PNG
  });

  testWidgets('un código de la lista, al abrirlo, también se puede compartir', (tester) async {
    var compartido = false;
    await pumpVisitas(
      tester,
      conUnCodigoLibre(),
      compartir: ({required codigo, required imagen, required texto}) async => compartido = codigo == 'libre-2',
    );

    await tester.tap(find.byKey(const Key('codigo_q2')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('compartir_codigo')));
    await tester.tap(find.byKey(const Key('compartir_codigo')));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 500)));
    await tester.pumpAndSettle();

    expect(compartido, isTrue);
  });

  testWidgets('si compartir falla, avisa y la pantalla sigue funcionando', (tester) async {
    await pumpVisitas(
      tester,
      conUnCodigoLibre(),
      compartir: ({required codigo, required imagen, required texto}) async =>
          throw Exception('sin app para compartir'),
    );

    await tester.tap(find.text('Generar código de visita'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('compartir_codigo')));
    await tester.tap(find.byKey(const Key('compartir_codigo')));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 500)));
    await tester.pumpAndSettle();

    expect(find.text('No se pudo compartir el código.'), findsOneWidget);
    expect(find.text('Compartir código'), findsOneWidget); // el botón vuelve a estar disponible
  });
}
