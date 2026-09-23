import 'package:app_residente/screens/login_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/auth_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpLogin(WidgetTester tester, AuthService authService, VoidCallback onLoginSuccess) async {
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(authService: authService, onLoginSuccess: onLoginSuccess),
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
