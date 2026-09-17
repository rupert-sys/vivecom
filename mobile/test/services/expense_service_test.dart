import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/expense_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureGastos = '''
[
  {"id": "g1", "categoria": "Jardinería", "monto": 1200.0, "comprobante_url": "https://example.com/r1.pdf", "fecha": "2026-09-01"},
  {"id": "g2", "categoria": "Seguridad", "monto": 8000.0, "comprobante_url": "https://example.com/r2.pdf", "fecha": "2026-08-15"}
]
''';

void main() {
  test('listarGastos pide /expenses sin filtros cuando no se pasa ninguno', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.toString(), 'http://localhost:8000/expenses');
      expect(request.headers['Authorization'], 'Bearer un-token');
      return http.Response(_fixtureGastos, 200);
    });
    final service = ExpenseService(api: ApiClient(client: mockClient));

    final gastos = await service.listarGastos('un-token');

    expect(gastos, hasLength(2));
    expect(gastos[0].categoria, 'Jardinería');
    expect(gastos[0].monto, 1200.0);
    expect(gastos[0].comprobanteUrl, 'https://example.com/r1.pdf');
    expect(gastos[0].fecha, DateTime(2026, 9, 1));
  });

  test('listarGastos manda desde/hasta/categoria como query params', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/expenses');
      expect(request.url.queryParameters['desde'], '2026-08-01');
      expect(request.url.queryParameters['hasta'], '2026-09-30');
      expect(request.url.queryParameters['categoria'], 'Jardinería');
      return http.Response('[]', 200);
    });
    final service = ExpenseService(api: ApiClient(client: mockClient));

    await service.listarGastos(
      'un-token',
      desde: DateTime(2026, 8, 1),
      hasta: DateTime(2026, 9, 30),
      categoria: 'Jardinería',
    );
  });

  test('ignora una categoría vacía o solo espacios', () async {
    final mockClient = MockClient((request) async {
      expect(request.url.queryParameters.containsKey('categoria'), isFalse);
      return http.Response('[]', 200);
    });
    final service = ExpenseService(api: ApiClient(client: mockClient));

    await service.listarGastos('un-token', categoria: '   ');
  });
}
