import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/cash_movement_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('CashMovementService', () {
    test('obtenerBalance pide /cash-movements/balance y mapea chica/grande', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.toString(), 'http://localhost:8000/cash-movements/balance');
        expect(request.headers['Authorization'], 'Bearer un-token');
        return http.Response('{"chica": 1500.0, "grande": 48000.0}', 200);
      });
      final service = CashMovementService(api: ApiClient(client: mockClient));

      final balance = await service.obtenerBalance('un-token');

      expect(balance.chica, 1500.0);
      expect(balance.grande, 48000.0);
    });

    test('propaga el mensaje de error del backend si falla', () async {
      final mockClient = MockClient((request) async {
        return http.Response('{"detail": "No autorizado"}', 401);
      });
      final service = CashMovementService(api: ApiClient(client: mockClient));

      expect(
        () => service.obtenerBalance('un-token'),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'No autorizado')),
      );
    });
  });
}
