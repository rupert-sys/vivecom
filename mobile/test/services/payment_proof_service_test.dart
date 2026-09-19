import 'dart:convert';

import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/payment_proof_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _comprobante = '''
{"id": "c1", "property_id": "p1", "monto": 750.0, "fecha_pago": "2026-09-04", "nota": "BBVA", "estado": "rechazado",
 "created_at": "2026-09-05T15:00:00", "revisado_en": "2026-09-06T10:00:00", "motivo_rechazo": "Ilegible", "payment_id": null,
 "archivo_url": "http://localhost:8000/files/f1/content?t=abc"}
''';

void main() {
  test('subirArchivo manda multipart con kind=pago, el archivo y el token, y regresa el id', () async {
    late http.BaseRequest capturada;
    final mockClient = MockClient((request) async {
      capturada = request;
      return http.Response(
        '{"id": "arch-1", "nombre_original": "banco.jpg", "content_type": "image/jpeg", "size": 4, "ref": "/files/arch-1"}',
        201,
      );
    });

    final id = await PaymentProofService(api: ApiClient(client: mockClient))
        .subirArchivo([1, 2, 3, 4], 'banco.jpg', 'un-token');

    expect(id, 'arch-1');
    expect(capturada.method, 'POST');
    expect(capturada.url.path, '/files');
    expect(capturada.headers['Authorization'], 'Bearer un-token');
    expect(capturada.headers['content-type'], startsWith('multipart/form-data; boundary='));
    final cuerpo = latin1.decode((capturada as http.Request).bodyBytes);
    expect(cuerpo, contains('name="kind"'));
    expect(cuerpo, contains('pago'));
    expect(cuerpo, contains('name="file"; filename="banco.jpg"'));
  });

  test('enviarComprobante manda monto, archivo, fecha y nota, y omite lo que no se llenó', () async {
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/payment-proofs');
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(_comprobante, 201);
    });
    final service = PaymentProofService(api: ApiClient(client: mockClient));

    await service.enviarComprobante(
      monto: 750,
      archivoId: 'arch-1',
      fechaPago: DateTime(2026, 9, 4),
      nota: '  BBVA  ',
      token: 't',
    );
    expect(cuerpo, {'monto': 750.0, 'archivo_id': 'arch-1', 'fecha_pago': '2026-09-04', 'nota': 'BBVA'});

    await service.enviarComprobante(monto: 100, archivoId: 'arch-2', nota: '   ', token: 't');
    expect(cuerpo, {'monto': 100.0, 'archivo_id': 'arch-2'});
  });

  test('listarMisComprobantes decodifica el estado, el motivo y el enlace firmado', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/payment-proofs');
      return http.Response('[$_comprobante]', 200);
    });

    final lista = await PaymentProofService(api: ApiClient(client: mockClient)).listarMisComprobantes('t');

    final c = lista.single;
    expect((c.estado, c.motivoRechazo, c.monto), ('rechazado', 'Ilegible', 750.0));
    expect(c.fechaPago, DateTime(2026, 9, 4));
    expect(c.createdAt.isUtc, isTrue);
    expect(c.archivoUrl, contains('/files/f1/content'));
  });

  test('lanza ApiException con el motivo del backend si la subida es rechazada', () async {
    final mockClient = MockClient(
      (request) async => http.Response('{"detail": "Solo se aceptan fotos (JPG, PNG, WEBP, HEIC) o PDF."}', 415),
    );

    expect(
      PaymentProofService(api: ApiClient(client: mockClient)).subirArchivo([1], 'x.exe', 't'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('Solo se aceptan fotos'))),
    );
  });
}
