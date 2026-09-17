import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/fee_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

String _iso(DateTime d) => d.toIso8601String().split('T').first;

void main() {
  group('FeeService.obtenerCuotaVigente', () {
    test('regresa la primera cuota cuya activa_desde ya pasó (la lista viene ordenada DESC del backend)', () async {
      final ayer = _iso(DateTime.now().subtract(const Duration(days: 1)));
      final haceUnAnio = _iso(DateTime.now().subtract(const Duration(days: 365)));
      final mockClient = MockClient((request) async {
        expect(request.url.toString(), 'http://localhost:8000/fees');
        return http.Response(
          '[{"id": "f2", "monto": 900.0, "periodicidad": "mensual", "activa_desde": "$ayer"},'
          '{"id": "f1", "monto": 800.0, "periodicidad": "mensual", "activa_desde": "$haceUnAnio"}]',
          200,
        );
      });
      final service = FeeService(api: ApiClient(client: mockClient));

      final cuota = await service.obtenerCuotaVigente('un-token');

      expect(cuota?.id, 'f2');
      expect(cuota?.monto, 900.0);
    });

    test('ignora una cuota cuya activa_desde todavía no llega', () async {
      final manana = _iso(DateTime.now().add(const Duration(days: 1)));
      final ayer = _iso(DateTime.now().subtract(const Duration(days: 1)));
      final mockClient = MockClient((request) async {
        return http.Response(
          '[{"id": "futura", "monto": 1000.0, "periodicidad": "mensual", "activa_desde": "$manana"},'
          '{"id": "vigente", "monto": 800.0, "periodicidad": "mensual", "activa_desde": "$ayer"}]',
          200,
        );
      });
      final service = FeeService(api: ApiClient(client: mockClient));

      final cuota = await service.obtenerCuotaVigente('un-token');

      expect(cuota?.id, 'vigente');
    });

    test('regresa null si no hay ninguna cuota vigente', () async {
      final mockClient = MockClient((request) async => http.Response('[]', 200));
      final service = FeeService(api: ApiClient(client: mockClient));

      expect(await service.obtenerCuotaVigente('un-token'), isNull);
    });
  });
}
