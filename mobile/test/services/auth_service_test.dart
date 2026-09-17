import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/auth_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('AuthService', () {
    test('login guarda el token que regresa el backend', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.toString(), 'http://localhost:8000/auth/login');
        return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
      });
      final auth = AuthService(api: ApiClient(client: mockClient));

      await auth.login('residente@example.com', 'secret123');

      expect(await auth.obtenerToken(), 'abc.def.ghi');
    });

    test('login propaga el mensaje de error del backend si las credenciales son inválidas', () async {
      final mockClient = MockClient((request) async {
        return http.Response('{"detail": "Credenciales inválidas"}', 401);
      });
      final auth = AuthService(api: ApiClient(client: mockClient));

      expect(
        () => auth.login('mal@example.com', 'incorrecta'),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Credenciales inválidas')),
      );
      expect(await auth.obtenerToken(), isNull);
    });

    test('logout borra el token guardado', () async {
      SharedPreferences.setMockInitialValues({'access_token': 'algo'});
      final auth = AuthService();

      expect(await auth.obtenerToken(), 'algo');
      await auth.logout();
      expect(await auth.obtenerToken(), isNull);
    });
  });

  group('TokenPayload.decode', () {
    test('decodifica sub, tenant_id, schema, rol y property_id del payload del JWT', () {
      // Mismo header/payload que produce app.core.security.create_access_token
      // en el backend, codificado a mano para no depender de una librería JWT
      // en el cliente (el mismo criterio que auth.ts del panel admin web).
      const token =
          'eyJhbGciOiJIUzI1NiJ9.'
          'eyJzdWIiOiJ1MSIsInRlbmFudF9pZCI6InQxIiwic2NoZW1hIjoidGVuYW50X2FiYyIsInJvbCI6InJlc2lkZW50ZSIsInByb3BlcnR5X2lkIjoicDEifQ.'
          'firma-no-verificada-en-el-cliente';

      final payload = TokenPayload.decode(token);

      expect(payload.sub, 'u1');
      expect(payload.tenantId, 't1');
      expect(payload.schema, 'tenant_abc');
      expect(payload.rol, 'residente');
      expect(payload.propertyId, 'p1');
    });
  });
}
