import 'dart:convert';

import 'package:app_residente/screens/login_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/auth_service.dart';
import 'package:app_residente/services/biometric_auth_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Doble de prueba: BiometricAuthService envuelve el plugin local_auth (canal de plataforma, no corre en
// `flutter test`) — se sustituye por esta subclase en vez de tocar el plugin real.
class _BiometricAuthServiceFalso extends BiometricAuthService {
  final bool disponible;
  _BiometricAuthServiceFalso({this.disponible = true});

  @override
  Future<bool> estaDisponible() async => disponible;
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpLogin(WidgetTester tester, AuthService authService, VoidCallback onLoginSuccess) async {
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authService: authService,
          onLoginSuccess: onLoginSuccess,
          // Sin este doble, "estaDisponible" tocaría el canal de plataforma real de local_auth, que no existe
          // en `flutter test` — en algunos entornos de prueba no lanza una excepción (que BiometricAuthService
          // ya sabe atrapar), sino que el Future simplemente nunca se resuelve, y el login se queda colgado
          // esperando una respuesta que no va a llegar.
          biometricService: _BiometricAuthServiceFalso(disponible: false),
        ),
      ),
    );
  }

  testWidgets('muestra los campos de email, contraseña y el botón Entrar', (tester) async {
    final auth = AuthService(api: ApiClient(client: MockClient((r) async => http.Response('{}', 200))));
    await pumpLogin(tester, auth, () {});

    expect(find.byKey(const Key('email_field')), findsOneWidget);
    expect(find.byKey(const Key('password_field')), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Entrar'), findsOneWidget);
  });

  testWidgets('un login exitoso llama a onLoginSuccess', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));
    var loginExitosoLlamado = false;

    await pumpLogin(tester, auth, () => loginExitosoLlamado = true);

    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(loginExitosoLlamado, isTrue);
  });

  testWidgets('sin marcar "Recordarme", el login manda recordar:false', (tester) async {
    var recordarMandado = true; // valor imposible: si no se sobrescribe, la prueba falla de forma obvia
    final mockClient = MockClient((request) async {
      recordarMandado = (jsonDecode(request.body) as Map<String, dynamic>)['recordar'] as bool;
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));

    await pumpLogin(tester, auth, () {});
    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(recordarMandado, isFalse);
  });

  testWidgets('marcar "Recordarme" manda recordar:true al backend', (tester) async {
    var recordarMandado = false;
    final mockClient = MockClient((request) async {
      recordarMandado = (jsonDecode(request.body) as Map<String, dynamic>)['recordar'] as bool;
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));

    await pumpLogin(tester, auth, () {});
    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.byKey(const Key('recordar_checkbox')));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(recordarMandado, isTrue);
  });

  testWidgets('con biométricos disponibles, un login exitoso ofrece activarlos', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));

    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authService: auth,
          biometricService: _BiometricAuthServiceFalso(),
          onLoginSuccess: () {},
        ),
      ),
    );
    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(find.text('Entrar más rápido'), findsOneWidget);
  });

  testWidgets('elegir "Sí, activar" prende la preferencia de biométricos y luego entra', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));
    var loginExitosoLlamado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authService: auth,
          biometricService: _BiometricAuthServiceFalso(),
          onLoginSuccess: () => loginExitosoLlamado = true,
        ),
      ),
    );
    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Sí, activar'));
    await tester.pumpAndSettle();

    expect(await auth.biometricosActivados(), isTrue);
    expect(loginExitosoLlamado, isTrue);
  });

  testWidgets('elegir "Ahora no" entra sin activar biométricos', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));
    var loginExitosoLlamado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authService: auth,
          biometricService: _BiometricAuthServiceFalso(),
          onLoginSuccess: () => loginExitosoLlamado = true,
        ),
      ),
    );
    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ahora no'));
    await tester.pumpAndSettle();

    expect(await auth.biometricosActivados(), isFalse);
    expect(loginExitosoLlamado, isTrue);
  });

  testWidgets('sin biométricos disponibles en el equipo, no se ofrece nada', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"access_token": "abc.def.ghi", "token_type": "bearer"}', 200);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));
    var loginExitosoLlamado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authService: auth,
          biometricService: _BiometricAuthServiceFalso(disponible: false),
          onLoginSuccess: () => loginExitosoLlamado = true,
        ),
      ),
    );
    await tester.enterText(find.byKey(const Key('email_field')), 'residente@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'secret123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(find.text('Entrar más rápido'), findsNothing);
    expect(loginExitosoLlamado, isTrue);
  });

  testWidgets('el enlace de registro lleva a RegistroScreen', (tester) async {
    final auth = AuthService(api: ApiClient(client: MockClient((r) async => http.Response('{}', 200))));
    await pumpLogin(tester, auth, () {});

    await tester.tap(find.byKey(const Key('ir_a_registro')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('condominio_field')), findsOneWidget);
  });

  testWidgets('un login fallido muestra el mensaje de error del backend', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "Credenciales inválidas"}', 401);
    });
    final auth = AuthService(api: ApiClient(client: mockClient));

    await pumpLogin(tester, auth, () {});

    await tester.enterText(find.byKey(const Key('email_field')), 'mal@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'incorrecta');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(find.text('Credenciales inválidas'), findsOneWidget);
  });
}
