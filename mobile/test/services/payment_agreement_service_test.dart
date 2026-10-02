import 'dart:convert';

import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/payment_agreement_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _vigente = '''
{"id": "a1", "property_id": "p1", "vivienda": "Casa 1", "estado": "vigente", "causa": "Perdí mi empleo en agosto.",
 "propuesta_pagos": 3, "propuesta_primer_pago": "2026-10-05", "capturado_por_staff": false, "created_at": "2026-09-18T15:00:00",
 "decidido_en": "2026-09-19T10:00:00", "motivo_rechazo": null, "archivo_url": null, "vigente_desde": "2026-09-19T10:00:00",
 "calendario": [{"fecha": "2026-10-05", "monto": 250.0}, {"fecha": "2026-11-05", "monto": 250.0}, {"fecha": "2026-12-05", "monto": 250.0}],
 "congela_recargo": true, "deuda_inicial": 750.0, "abonado": 250.0, "pendiente_cubierto": 500.0,
 "proximo_pago": {"fecha": "2026-11-05", "monto": 250.0}, "incumplimientos_previos": 0}
''';

void main() {
  test('listarMisAcuerdos decodifica el calendario, el avance y el próximo pago', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/payment-agreements');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response('[$_vigente]', 200);
    });

    final acuerdos = await PaymentAgreementService(api: ApiClient(client: mockClient)).listarMisAcuerdos('un-token');

    final a = acuerdos.single;
    expect((a.estado, a.abierto, a.congelaRecargo), ('vigente', true, true));
    expect((a.deudaInicial, a.abonado, a.pendienteCubierto), (750.0, 250.0, 500.0));
    expect(a.calendario.map((p) => p.monto), [250.0, 250.0, 250.0]);
    expect(a.calendario.first.fecha, DateTime(2026, 10, 5));
    expect((a.proximoPago!.monto, a.proximoPago!.fecha), (250.0, DateTime(2026, 11, 5)));
    expect(a.createdAt.isUtc, isTrue); // naive-UTC del backend
  });

  test('una solicitud pendiente aún no trae calendario ni avance', () async {
    final pendiente = _vigente
        .replaceFirst('"estado": "vigente"', '"estado": "solicitado"')
        .replaceFirst(RegExp(r'"calendario": \[.*?\],', dotAll: true), '"calendario": null,')
        .replaceFirst('"proximo_pago": {"fecha": "2026-11-05", "monto": 250.0}', '"proximo_pago": null');
    final mockClient = MockClient((request) async => http.Response('[$pendiente]', 200));

    final a = (await PaymentAgreementService(api: ApiClient(client: mockClient)).listarMisAcuerdos('t')).single;

    expect((a.estado, a.abierto), ('solicitado', true));
    expect(a.calendario, isEmpty);
    expect(a.proximoPago, isNull);
  });

  test('solicitar manda la causa, los pagos, la fecha y el documento solo si lo hay', () async {
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/payment-agreements');
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(_vigente, 201);
    });
    final service = PaymentAgreementService(api: ApiClient(client: mockClient));

    await service.solicitar(
      causa: '  Perdí mi empleo en agosto.  ',
      numeroDePagos: 3,
      primerPago: DateTime(2026, 10, 5),
      token: 't',
    );
    expect(cuerpo, {'causa': 'Perdí mi empleo en agosto.', 'numero_de_pagos': 3, 'primer_pago': '2026-10-05'});

    await service.solicitar(
      causa: 'x' * 30,
      numeroDePagos: 1,
      primerPago: DateTime(2026, 10, 5),
      archivoId: 'arch-1',
      token: 't',
    );
    expect(cuerpo!['archivo_id'], 'arch-1');
  });

  test('subirDocumento manda multipart con kind=acuerdo y regresa el id', () async {
    late http.BaseRequest capturada;
    final mockClient = MockClient((request) async {
      capturada = request;
      return http.Response(
        '{"id": "arch-7", "nombre_original": "carta.pdf", "content_type": "application/pdf", "size": 3, "ref": "/files/arch-7"}',
        201,
      );
    });

    final id = await PaymentAgreementService(api: ApiClient(client: mockClient))
        .subirDocumento([1, 2, 3], 'carta.pdf', 't');

    expect(id, 'arch-7');
    final cuerpo = latin1.decode((capturada as http.Request).bodyBytes);
    expect(cuerpo, contains('acuerdo'));
    expect(cuerpo, contains('filename="carta.pdf"'));
  });

  test('retirarSolicitud pide POST /payment-agreements/{id}/cancel', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/payment-agreements/a1/cancel');
      return http.Response(_vigente.replaceFirst('"estado": "vigente"', '"estado": "cancelado"'), 200);
    });

    final a = await PaymentAgreementService(api: ApiClient(client: mockClient)).retirarSolicitud('a1', 't');

    expect(a.estado, 'cancelado');
    expect(a.abierto, isFalse);
  });

  test('solicitar lanza ApiException con el motivo del backend (plazo máximo, adeudo, ya hay uno abierto)', () async {
    final mockClient = MockClient(
      (request) async => http.Response('{"detail": "El acuerdo debe quedar liquidado en un máximo de 3 meses."}', 422),
    );

    expect(
      PaymentAgreementService(api: ApiClient(client: mockClient))
          .solicitar(causa: 'x' * 25, numeroDePagos: 6, primerPago: DateTime(2026, 10, 5), token: 't'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('máximo de 3 meses'))),
    );
  });
}
