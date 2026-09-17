import 'dart:convert';

import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/auth_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

String _tokenConRol(String rol) {
  final header = base64Url.encode(utf8.encode('{"alg":"none"}')).replaceAll('=', '');
  final payload = base64Url
      .encode(utf8.encode(jsonEncode({'sub': 'u1', 'tenant_id': 't1', 'schema': 'tenant_t1', 'rol': rol})))
      .replaceAll('=', '');
  return '$header.$payload.firma';
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('AuthService login guarda el token que regresa el backend', () async {
    final mockClient = MockClient((request) async => http.Response('{"access_token": "${_tokenConRol('guardia')}"}', 200));
    final auth = AuthService(api: ApiClient(client: mockClient));

    await auth.login('guardia@example.com', 'secret123');

    expect(await auth.obtenerToken(), _tokenConRol('guardia'));
  });

  test('AuthService login propaga el mensaje de error del backend si las credenciales son inválidas', () async {
    final mockClient = MockClient((request) async => http.Response('{"detail": "Credenciales inválidas"}', 401));
    final auth = AuthService(api: ApiClient(client: mockClient));

    expect(() => auth.login('mal@example.com', 'incorrecta'), throwsA(isA<ApiException>()));
  });

  test('AuthService logout borra el token guardado', () async {
    SharedPreferences.setMockInitialValues({'access_token': _tokenConRol('guardia')});
    final auth = AuthService();

    await auth.logout();

    expect(await auth.obtenerToken(), isNull);
  });

  test('TokenPayload.decode decodifica sub, tenant_id, schema y rol del payload del JWT', () {
    final payload = TokenPayload.decode(_tokenConRol('guardia'));

    expect(payload.sub, 'u1');
    expect(payload.tenantId, 't1');
    expect(payload.schema, 'tenant_t1');
    expect(payload.rol, 'guardia');
  });
}
