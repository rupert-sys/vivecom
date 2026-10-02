import 'dart:convert';

import 'package:app_residente/screens/payment_agreement_screen.dart';
import 'package:app_residente/screens/payment_proof_screen.dart' show ArchivoElegido, SeleccionarArchivo;
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/payment_agreement_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

String _acuerdo({String id = 'a1', String estado = 'solicitado', String? motivo, bool conCalendario = false}) =>
    '{"id": "$id", "property_id": "p1", "vivienda": "Casa 1", "estado": "$estado", "causa": "Perdí mi empleo en agosto.", '
    '"propuesta_pagos": 3, "propuesta_primer_pago": "2026-10-05", "capturado_por_staff": false, "created_at": "2026-09-18T15:00:00", '
    '"decidido_en": null, "motivo_rechazo": ${motivo == null ? 'null' : '"$motivo"'}, "archivo_url": null, "vigente_desde": null, '
    '"calendario": ${conCalendario ? '[{"fecha": "2026-10-05", "monto": 250.0}, {"fecha": "2026-11-05", "monto": 250.0}, {"fecha": "2026-12-05", "monto": 250.0}]' : 'null'}, '
    '"congela_recargo": ${conCalendario ? 'true' : 'null'}, "deuda_inicial": ${conCalendario ? '750.0' : 'null'}, '
    '"abonado": ${conCalendario ? '250.0' : 'null'}, "pendiente_cubierto": ${conCalendario ? '500.0' : 'null'}, '
    '"proximo_pago": ${conCalendario ? '{"fecha": "2026-11-05", "monto": 250.0}' : 'null'}, "incumplimientos_previos": 0}';

const _causaValida = 'Perdí mi empleo en agosto y regularizo mis ingresos.';

void main() {
  Future<void> pumpPantalla(WidgetTester tester, http.Client client, {SeleccionarArchivo? seleccionar}) async {
    tester.view.physicalSize = const Size(800, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        home: PaymentAgreementScreen(
          token: 'un-token',
          agreementService: PaymentAgreementService(api: ApiClient(client: client)),
          seleccionarArchivo: seleccionar ?? (_) async => null,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> elegirFecha(WidgetTester tester) async {
    await tester.tap(find.byKey(const Key('primer_pago_button')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
  }

  testWidgets('sin acuerdos muestra el formulario para solicitarlo', (tester) async {
    await pumpPantalla(tester, MockClient((request) async => http.Response('[]', 200)));

    expect(find.text('¿No puedes pagar a tiempo?'), findsOneWidget);
    expect(find.text('Enviar solicitud'), findsOneWidget);
    expect(find.byKey(const Key('acuerdo_vigente')), findsNothing);
  });

  testWidgets('valida la causa (mínimo 20 caracteres) y la fecha antes de enviar', (tester) async {
    var posts = 0;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') posts++;
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.enterText(find.byKey(const Key('causa_field')), 'Ya no puedo');
    await tester.tap(find.text('Enviar solicitud'));
    await tester.pumpAndSettle();
    expect(find.textContaining('al menos 20 caracteres'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('causa_field')), _causaValida);
    await tester.tap(find.text('Enviar solicitud'));
    await tester.pumpAndSettle();
    expect(find.text('Elige la fecha de tu primer pago.'), findsOneWidget);
    expect(posts, 0);
  });

  testWidgets('envía la solicitud con la causa, los pagos y la fecha, y pasa a "en revisión"', (tester) async {
    Map<String, dynamic>? cuerpo;
    var enviada = false;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/payment-agreements') {
        cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
        enviada = true;
        return http.Response(_acuerdo(), 201);
      }
      return http.Response(enviada ? '[${_acuerdo()}]' : '[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.enterText(find.byKey(const Key('causa_field')), _causaValida);
    await tester.tap(find.byKey(const Key('numero_de_pagos')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('3 pagos').last);
    await tester.pumpAndSettle();
    await elegirFecha(tester);
    await tester.tap(find.text('Enviar solicitud'));
    await tester.pumpAndSettle();

    expect(cuerpo!['causa'], _causaValida);
    expect(cuerpo!['numero_de_pagos'], 3);
    expect(cuerpo!['primer_pago'], matches(RegExp(r'^\d{4}-\d{2}-\d{2}$')));
    expect(cuerpo!.containsKey('archivo_id'), isFalse);
    expect(find.byKey(const Key('acuerdo_solicitado')), findsOneWidget);
    expect(find.text('Enviar solicitud'), findsNothing); // ya hay una solicitud abierta: no se pide otra
  });

  testWidgets('sube el documento de respaldo primero y la solicitud lleva su id', (tester) async {
    final rutas = <String>[];
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      rutas.add('${request.method} ${request.url.path}');
      if (request.url.path == '/files') {
        return http.Response(
          '{"id": "arch-3", "nombre_original": "carta.pdf", "content_type": "application/pdf", "size": 4, "ref": "/files/arch-3"}',
          201,
        );
      }
      if (request.method == 'POST') {
        cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(_acuerdo(), 201);
      }
      return http.Response('[]', 200);
    });

    await pumpPantalla(
      tester,
      mockClient,
      seleccionar: (_) async => ArchivoElegido(nombre: 'carta.pdf', bytes: [1, 2, 3, 4]),
    );
    await tester.enterText(find.byKey(const Key('causa_field')), _causaValida);
    await tester.tap(find.byKey(const Key('elegir_pdf_acuerdo')));
    await tester.pumpAndSettle();
    expect(find.text('Adjunto: carta.pdf'), findsOneWidget);
    await elegirFecha(tester);
    await tester.tap(find.text('Enviar solicitud'));
    await tester.pumpAndSettle();

    expect(rutas, containsAllInOrder(['POST /files', 'POST /payment-agreements']));
    expect(cuerpo!['archivo_id'], 'arch-3');
  });

  testWidgets('un documento de más de 10 MB se rechaza sin subirlo', (tester) async {
    var posts = 0;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') posts++;
      return http.Response('[]', 200);
    });

    await pumpPantalla(
      tester,
      mockClient,
      seleccionar: (_) async => ArchivoElegido(nombre: 'x.pdf', bytes: List.filled(10 * 1024 * 1024 + 1, 0)),
    );
    await tester.tap(find.byKey(const Key('elegir_pdf_acuerdo')));
    await tester.pumpAndSettle();

    expect(find.textContaining('pesa más de 10 MB'), findsOneWidget);
    expect(find.byKey(const Key('documento_elegido')), findsNothing);
    expect(posts, 0);
  });

  testWidgets('muestra el motivo del backend si rechaza la solicitud (plazo máximo)', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.method == 'POST') {
        return http.Response('{"detail": "El acuerdo debe quedar liquidado en un máximo de 3 meses"}', 422);
      }
      return http.Response('[]', 200);
    });

    await pumpPantalla(tester, mockClient);
    await tester.enterText(find.byKey(const Key('causa_field')), _causaValida);
    await elegirFecha(tester);
    await tester.tap(find.text('Enviar solicitud'));
    await tester.pumpAndSettle();

    expect(find.textContaining('máximo de 3 meses'), findsOneWidget);
    expect(find.byKey(const Key('acuerdo_solicitado')), findsNothing);
  });

  testWidgets('una solicitud en revisión se puede retirar y vuelve el formulario', (tester) async {
    var retirada = false;
    final mockClient = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/payment-agreements/a1/cancel') {
        retirada = true;
        return http.Response(_acuerdo(estado: 'cancelado'), 200);
      }
      return http.Response(retirada ? '[${_acuerdo(estado: 'cancelado')}]' : '[${_acuerdo()}]', 200);
    });

    await pumpPantalla(tester, mockClient);
    expect(find.text('Tu solicitud está en revisión'), findsOneWidget);
    await tester.tap(find.byKey(const Key('retirar_solicitud')));
    await tester.pumpAndSettle();

    expect(retirada, isTrue);
    expect(find.text('Enviar solicitud'), findsOneWidget);
    expect(find.text('Cancelado'), findsOneWidget); // queda en "Anteriores"
  });

  testWidgets('un acuerdo vigente muestra el avance, el próximo pago, el calendario y que el recargo está congelado', (
    tester,
  ) async {
    final mockClient = MockClient(
      (request) async => http.Response('[${_acuerdo(estado: 'vigente', conCalendario: true)}]', 200),
    );

    await pumpPantalla(tester, mockClient);

    expect(find.byKey(const Key('acuerdo_vigente')), findsOneWidget);
    expect(find.text('Llevas \$250.00 de \$750.00'), findsOneWidget);
    expect(find.textContaining('Próximo pago: \$250.00 el 2026-11-05'), findsOneWidget);
    expect(find.text('• 2026-10-05: \$250.00'), findsOneWidget);
    expect(find.text('• 2026-12-05: \$250.00'), findsOneWidget);
    expect(find.byKey(const Key('recargo_congelado')), findsOneWidget);
    expect(find.text('Enviar solicitud'), findsNothing); // ya hay un acuerdo abierto
  });

  testWidgets('los acuerdos anteriores muestran su resultado y, si incumplió, que vuelve a estar en mora', (
    tester,
  ) async {
    final mockClient = MockClient((request) async {
      return http.Response(
        '[${_acuerdo(id: 'r', estado: 'rechazado', motivo: 'No se acreditó la causa')}, ${_acuerdo(id: 'i', estado: 'incumplido')}, ${_acuerdo(id: 'c', estado: 'cumplido')}]',
        200,
      );
    });

    await pumpPantalla(tester, mockClient);

    expect(find.textContaining('Motivo: No se acreditó la causa'), findsOneWidget);
    expect(find.textContaining('Vuelves a estar en mora'), findsOneWidget);
    expect(find.text('Cumplido'), findsOneWidget);
    expect(find.text('Enviar solicitud'), findsOneWidget); // ninguno abierto: puede solicitar otro
  });

  testWidgets('si no cargan los acuerdos muestra el error', (tester) async {
    await pumpPantalla(tester, MockClient((request) async => http.Response('{"detail": "Sin acceso"}', 403)));

    expect(find.text('Sin acceso'), findsOneWidget);
  });
}
