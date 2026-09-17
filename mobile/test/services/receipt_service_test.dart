import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/receipt_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('descargarRecibo pide /payments/{id}/receipt con el token y regresa los bytes', () async {
    final bytesEsperados = [0x25, 0x50, 0x44, 0x46]; // "%PDF"
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/payments/pg1/receipt');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response.bytes(bytesEsperados, 200);
    });
    final service = ReceiptService(api: ApiClient(client: mockClient));

    final bytes = await service.descargarRecibo('pg1', 'un-token');

    expect(bytes, bytesEsperados);
  });

  test('lanza ApiException con el mensaje del backend si el pago no está confirmado (409)', () async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "Solo hay recibo para pagos confirmados"}', 409);
    });
    final service = ReceiptService(api: ApiClient(client: mockClient));

    expect(
      () => service.descargarRecibo('pg1', 'un-token'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Solo hay recibo para pagos confirmados')),
    );
  });
}
