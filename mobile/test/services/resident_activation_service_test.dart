import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/resident_activation_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('preview pide GET /residents/activar/preview con el condominio y número de casa, sin token', () async {
    final mockClient = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/residents/activar/preview');
      expect(request.url.queryParameters['nombre_condominio'], 'Condominio Arequipa');
      expect(request.url.queryParameters['numero_de_casa'], '5');
      expect(request.headers['Authorization'], isNull);
      return http.Response('{"email": "casa5@arequipa.com.mx", "identificador": "Casa 5"}', 200);
    });
    final service = ResidentActivationService(api: ApiClient(client: mockClient));

    final preview = await service.preview(nombreCondominio: 'Condominio Arequipa', numeroDeCasa: 5);

    expect(preview.email, 'casa5@arequipa.com.mx');
    expect(preview.identificador, 'Casa 5');
  });

  test('preview lanza ApiException con el motivo del backend si no hay ninguna vivienda sin activar con ese número', () async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "No hay ninguna vivienda sin activar con ese número"}', 404);
    });
    final service = ResidentActivationService(api: ApiClient(client: mockClient));

    expect(
      () => service.preview(nombreCondominio: 'Condominio Arequipa', numeroDeCasa: 99),
      throwsA(isA<ApiException>()),
    );
  });

  test('activar manda todos los datos del registro y regresa el access_token', () async {
    final mockClient = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/residents/activar');
      expect(request.body, contains('"nombre_condominio":"Condominio Arequipa"'));
      expect(request.body, contains('"numero_de_casa":5'));
      expect(request.body, contains('"nombre_completo":"Ana Torres"'));
      expect(request.body, contains('"rol":"propietario"'));
      expect(request.body, contains('"telefono":"5551234567"'));
      expect(request.body, contains('"password":"clave-de-ana-1"'));
      return http.Response('{"access_token": "un-token-nuevo", "token_type": "bearer"}', 200);
    });
    final service = ResidentActivationService(api: ApiClient(client: mockClient));

    final token = await service.activar(
      nombreCondominio: 'Condominio Arequipa',
      numeroDeCasa: 5,
      nombreCompleto: 'Ana Torres',
      rol: 'propietario',
      telefono: '5551234567',
      password: 'clave-de-ana-1',
    );

    expect(token, 'un-token-nuevo');
  });

  test('activar lanza ApiException si la vivienda ya fue reclamada', () async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "No hay ninguna vivienda sin activar con ese número"}', 404);
    });
    final service = ResidentActivationService(api: ApiClient(client: mockClient));

    expect(
      () => service.activar(
        nombreCondominio: 'Condominio Arequipa', numeroDeCasa: 5, nombreCompleto: 'Ana Torres',
        rol: 'propietario', telefono: '5551234567', password: 'clave-de-ana-1',
      ),
      throwsA(isA<ApiException>()),
    );
  });
}
