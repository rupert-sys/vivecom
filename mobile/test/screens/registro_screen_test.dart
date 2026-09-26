import 'package:app_residente/screens/registro_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/auth_service.dart';
import 'package:app_residente/services/resident_activation_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pump(
    WidgetTester tester, {
    required http.Client httpClient,
    VoidCallback? onRegistroExitoso,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        home: RegistroScreen(
          authService: AuthService(api: ApiClient(client: httpClient)),
          activationService: ResidentActivationService(api: ApiClient(client: httpClient)),
          onRegistroExitoso: onRegistroExitoso ?? () {},
        ),
      ),
    );
  }

  testWidgets('dice que el condominio ya debe existir, no que esta pantalla lo va a crear', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{}', 404));
    await pump(tester, httpClient: mockClient);

    expect(find.text('Regístrate como residente'), findsOneWidget);
    expect(find.textContaining('ya debe estar dado de alta por su administrador'), findsOneWidget);
  });

  testWidgets('al escribir condominio y número de casa y salir del campo, muestra el usuario que le tocará', (tester) async {
    final mockClient = MockClient((request) async {
      expect(request.url.path, '/residents/activar/preview');
      return http.Response('{"email": "casa5@arequipa.com.mx", "identificador": "Casa 5"}', 200);
    });
    await pump(tester, httpClient: mockClient);

    await tester.enterText(find.byKey(const Key('condominio_field')), 'Condominio Arequipa');
    await tester.enterText(find.byKey(const Key('casa_field')), '5');
    // Simula perder el foco (blur) tocando otro campo — el preview se dispara ahí, no al teclear.
    await tester.tap(find.byKey(const Key('nombre_field')));
    await tester.pumpAndSettle();

    expect(find.text('Tu usuario será: casa5@arequipa.com.mx'), findsOneWidget);
  });

  testWidgets('si el número de casa no existe, muestra el error del backend en vez del usuario', (tester) async {
    final mockClient = MockClient((request) async {
      return http.Response('{"detail": "No hay ninguna vivienda sin activar con ese número"}', 404);
    });
    await pump(tester, httpClient: mockClient);

    await tester.enterText(find.byKey(const Key('condominio_field')), 'Condominio Arequipa');
    await tester.enterText(find.byKey(const Key('casa_field')), '99');
    await tester.tap(find.byKey(const Key('nombre_field')));
    await tester.pumpAndSettle();

    expect(find.text('No hay ninguna vivienda sin activar con ese número'), findsOneWidget);
  });

  testWidgets('el botón Registrarme sigue deshabilitado hasta verificar la vivienda y llenar todo', (tester) async {
    final mockClient = MockClient((request) async => http.Response('{}', 404));
    await pump(tester, httpClient: mockClient);

    final boton = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Registrarme'));
    expect(boton.onPressed, isNull);
  });

  testWidgets('completar el registro llama a onRegistroExitoso, sin correo si se dejó vacío', (tester) async {
    String? cuerpoEnviado;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/residents/activar/preview') {
        return http.Response('{"email": "casa5@arequipa.com.mx", "identificador": "Casa 5"}', 200);
      }
      expect(request.url.path, '/residents/activar');
      cuerpoEnviado = request.body;
      return http.Response('{"access_token": "un-token-nuevo", "token_type": "bearer"}', 200);
    });
    var exitosoLlamado = false;
    await pump(tester, httpClient: mockClient, onRegistroExitoso: () => exitosoLlamado = true);

    await tester.enterText(find.byKey(const Key('condominio_field')), 'Condominio Arequipa');
    await tester.enterText(find.byKey(const Key('casa_field')), '5');
    await tester.enterText(find.byKey(const Key('nombre_field')), 'Ana Torres');
    await tester.pumpAndSettle(); // dispara la verificación (blur del campo de casa)
    await tester.enterText(find.byKey(const Key('telefono_field')), '5551234567');
    await tester.enterText(find.byKey(const Key('password_field')), 'clave-de-ana-1');
    await tester.pumpAndSettle();

    // El texto explicativo de arriba empuja el botón fuera del área visible en la pantalla de prueba.
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Registrarme'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrarme'));
    await tester.pumpAndSettle();

    expect(exitosoLlamado, isTrue);
    expect(cuerpoEnviado, isNot(contains('correo')));
  });

  testWidgets('si se llena el correo, se manda en el registro', (tester) async {
    String? cuerpoEnviado;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/residents/activar/preview') {
        return http.Response('{"email": "casa5@arequipa.com.mx", "identificador": "Casa 5"}', 200);
      }
      cuerpoEnviado = request.body;
      return http.Response('{"access_token": "un-token-nuevo", "token_type": "bearer"}', 200);
    });
    await pump(tester, httpClient: mockClient);

    await tester.enterText(find.byKey(const Key('condominio_field')), 'Condominio Arequipa');
    await tester.enterText(find.byKey(const Key('casa_field')), '5');
    await tester.enterText(find.byKey(const Key('nombre_field')), 'Ana Torres');
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('telefono_field')), '5551234567');
    await tester.enterText(find.byKey(const Key('correo_field')), 'ana@example.com');
    await tester.enterText(find.byKey(const Key('password_field')), 'clave-de-ana-1');
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Registrarme'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrarme'));
    await tester.pumpAndSettle();

    expect(cuerpoEnviado, contains('"correo":"ana@example.com"'));
  });

  testWidgets('un registro fallido muestra el mensaje de error del backend', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/residents/activar/preview') {
        return http.Response('{"email": "casa5@arequipa.com.mx", "identificador": "Casa 5"}', 200);
      }
      return http.Response('{"detail": "No hay ninguna vivienda sin activar con ese número"}', 404);
    });
    await pump(tester, httpClient: mockClient);

    await tester.enterText(find.byKey(const Key('condominio_field')), 'Condominio Arequipa');
    await tester.enterText(find.byKey(const Key('casa_field')), '5');
    await tester.enterText(find.byKey(const Key('nombre_field')), 'Ana Torres');
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('telefono_field')), '5551234567');
    await tester.enterText(find.byKey(const Key('password_field')), 'clave-de-ana-1');
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Registrarme'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Registrarme'));
    await tester.pumpAndSettle();

    expect(find.text('No hay ninguna vivienda sin activar con ese número'), findsOneWidget);
  });
}
