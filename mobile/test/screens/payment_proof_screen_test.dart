import 'dart:convert';

import 'package:app_residente/screens/expenses_screen.dart' show AbrirUrl;
import 'package:app_residente/screens/payment_proof_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/payment_proof_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

String _comprobante({String id = 'c1', String estado = 'pendiente', String? motivo, double monto = 750}) =>
    '{"id": "$id", "property_id": "p1", "monto": $monto, "fecha_pago": null, "nota": null, "estado": "$estado", '
    '"created_at": "2026-09-05T15:00:00", "revisado_en": null, "motivo_rechazo": ${motivo == null ? 'null' : '"$motivo"'}, '
    '"payment_id": null, "archivo_url": "http://localhost:8000/files/f1/content?t=abc"}';

final _foto = ArchivoElegido(nombre: 'captura.jpg', bytes: List.filled(2048, 1));

void main() {
  Future<void> pumpPantalla(
    WidgetTester tester,
    http.Client client, {
    SeleccionarArchivo? seleccionar,
    AbrirUrl? abrirUrl,
  }) async {
    // El formulario es largo y un ListView solo construye lo visible: una pantalla alta muestra todo.
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: PaymentProofScreen(
          token: 'un-token',
          proofService: PaymentProofService(api: ApiClient(client: client)),
          seleccionarArchivo: seleccionar ?? (_) async => _foto,
          abrirUrl: abrirUrl ?? (url) async {},
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('sin comprobantes muestra el mensaje vacío y el formulario', (tester) async {
    await pumpPantalla(tester, MockClient((request) async => http.Response('[]', 200)));

    expect(find.text('Todavía no has enviado comprobantes.'), findsOneWidget);
    expect(find.text('¿Ya pagaste?'), findsOneWidget);
    expect(find.text('Enviar comprobante'), findsOneWidget);
  });

  testWidgets('lista los comprobantes con su estado y el motivo si fue rechazado', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response(
        '[${_comprobante(id: 'a', monto: 750)}, ${_comprobante(id: 'b', estado: 'rechazado', motivo: 'Comprobante ilegible', monto: 300)}, '
        '${_comprobante(id: 'c', estado: 'aceptado', monto: 100)}]',
        200,
      );
    });

    await pumpPantalla(tester, mockClient);

    expect(find.text('\$750.00 · En revisión'), findsOneWidget);
    expect(find.text('\$100.00 · Aceptado'), findsOneWidget);
    expect(find.text('\$300.00 · Rechazado'), findsOneWidget);
    expect(find.textContaining('Motivo: Comprobante ilegible'), findsOneWidget);
  });

  testWidgets('tocar el clip abre el archivo con su enlace firmado', (tester) async {
    String? abierta;
    final mockClient = MockClient((request) async => http.Response('[${_comprobante()}]', 200));

    await pumpPantalla(tester, mockClient, abrirUrl: (url) async => abierta = url);
    await tester.tap(find.byKey(const Key('ver_comprobante_c1')));

    expect(abierta, 'http://localhost:8000/files/f1/content?t=abc');
  });

  testWidgets('elegir una foto muestra su nombre y peso', (tester) async {
    await pumpPantalla(tester, MockClient((request) async => http.Response('[]', 200)));

    await tester.tap(find.byKey(const Key('elegir_foto_button')));
    await tester.pumpAndSettle();

    expect(find.text('Archivo: captura.jpg (2 KB)'), findsOneWidget);
  });

  testWidgets('el selector recibe el origen: foto o PDF', (tester) async {
    final origenes = <OrigenDelArchivo>[];
    await pumpPantalla(
      tester,
      MockClient((request) async => http.Response('[]', 200)),
      seleccionar: (origen) async {
        origenes.add(origen);
        return null; // el usuario cancela
      },
    );

    await tester.tap(find.byKey(const Key('elegir_foto_button')));
    await tester.tap(find.byKey(const Key('elegir_pdf_button')));
    await tester.pumpAndSettle();

    expect(origenes, [OrigenDelArchivo.foto, OrigenDelArchivo.pdf]);
    expect(find.byKey(const Key('archivo_elegido')), findsNothing);
  });

  testWidgets('sube el archivo, manda el comprobante y lo muestra en la lista', (tester) async {
    final rutas = <String>[];
    Map<String, dynamic>? cuerpoDelComprobante;
    var enviado = false;
    final mockClient = MockClient((request) async {
      rutas.add('${request.method} ${request.url.path}');
      if (request.url.path == '/files') {
        return http.Response(
          '{"id": "arch-9", "nombre_original": "captura.jpg", "content_type": "image/jpeg", "size": 2048, "ref": "/files/arch-9"}',
          201,
        );
      }
      if (request.method == 'POST' && request.url.path == '/payment-proofs') {
        cuerpoDelComprobante = jsonDecode(request.body) as Map<String, dynamic>;
        enviado = true;
        return http.Response(_comprobante(), 201);
      }
      return http.Response(enviado ? '[${_comprobante()}]' : '[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.enterText(find.byKey(const Key('monto_comprobante_field')), '750,50');
    await tester.enterText(find.byKey(const Key('nota_comprobante_field')), 'BBVA');
    await tester.tap(find.byKey(const Key('elegir_foto_button')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar comprobante'));
    await tester.pumpAndSettle();

    expect(rutas, containsAllInOrder(['POST /files', 'POST /payment-proofs']));
    expect(cuerpoDelComprobante, {'monto': 750.5, 'archivo_id': 'arch-9', 'nota': 'BBVA'});
    expect(find.byKey(const Key('comprobante_enviado')), findsOneWidget);
    expect(find.text('\$750.00 · En revisión'), findsOneWidget);
    // el formulario queda limpio
    expect(tester.widget<TextField>(find.byKey(const Key('monto_comprobante_field'))).controller!.text, isEmpty);
    expect(find.byKey(const Key('archivo_elegido')), findsNothing);
  });

  testWidgets('no envía sin monto ni sin archivo', (tester) async {
    var llamadas = 0;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') llamadas++;
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.tap(find.text('Enviar comprobante'));
    await tester.pumpAndSettle();
    expect(find.text('Escribe el monto que pagaste.'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('monto_comprobante_field')), '750');
    await tester.tap(find.text('Enviar comprobante'));
    await tester.pumpAndSettle();
    expect(find.text('Adjunta la foto o el PDF de tu comprobante.'), findsOneWidget);
    expect(llamadas, 0);
  });

  testWidgets('un archivo de más de 10 MB se rechaza sin subirlo', (tester) async {
    var llamadas = 0;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') llamadas++;
      return http.Response('[]', 200);
    });
    final enorme = ArchivoElegido(nombre: 'video.pdf', bytes: List.filled(pesoMaximoDelComprobante + 1, 0));

    await pumpPantalla(tester, mockClient, seleccionar: (_) async => enorme);
    await tester.tap(find.byKey(const Key('elegir_pdf_button')));
    await tester.pumpAndSettle();

    expect(find.textContaining('pesa más de 10 MB'), findsOneWidget);
    expect(find.byKey(const Key('archivo_elegido')), findsNothing);
    expect(llamadas, 0);
  });

  testWidgets('muestra el motivo del backend si el archivo no es aceptado y conserva lo capturado', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/files') {
        return http.Response('{"detail": "Solo se aceptan fotos (JPG, PNG, WEBP, HEIC) o PDF."}', 415);
      }
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.enterText(find.byKey(const Key('monto_comprobante_field')), '750');
    await tester.tap(find.byKey(const Key('elegir_foto_button')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enviar comprobante'));
    await tester.pumpAndSettle();

    expect(find.text('Solo se aceptan fotos (JPG, PNG, WEBP, HEIC) o PDF.'), findsOneWidget);
    expect(find.byKey(const Key('comprobante_enviado')), findsNothing);
    expect(tester.widget<TextField>(find.byKey(const Key('monto_comprobante_field'))).controller!.text, '750');
  });

  testWidgets('si no cargan los comprobantes muestra el error', (tester) async {
    await pumpPantalla(tester, MockClient((request) async => http.Response('{"detail": "Sin acceso"}', 403)));

    expect(find.text('Sin acceso'), findsOneWidget);
  });
}
