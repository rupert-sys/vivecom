import 'package:app_residente/screens/login_screen.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/auth_service.dart';
import 'package:app_residente/services/biometric_auth_service.dart';
import 'package:app_residente/widgets/anadir_a_inicio.dart';
import 'package:app_residente/widgets/descarga_apk.dart';
import 'package:app_residente/widgets/instalar_app.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Doble de prueba: BiometricAuthService envuelve el plugin local_auth (canal de plataforma, no corre en
// `flutter test` — ver login_screen_test.dart para el porqué es necesario, no solo por estilo).
class _BiometricAuthServiceFalso extends BiometricAuthService {
  @override
  Future<bool> estaDisponible() async => false;
}

void main() {
  test('solo se ofrece el APK en la web abierta desde un Android', () {
    expect(debeOfrecerApk(esWeb: true, plataforma: TargetPlatform.android), isTrue);
    expect(debeOfrecerApk(esWeb: true, plataforma: TargetPlatform.iOS), isFalse); // el iPhone usa la web instalable
    expect(debeOfrecerApk(esWeb: true, plataforma: TargetPlatform.macOS), isFalse);
    expect(
      debeOfrecerApk(esWeb: false, plataforma: TargetPlatform.android),
      isFalse,
    ); // la app ya instalada no lo necesita
  });

  test('el enlace apunta al APK en la raíz del sitio, sin importar la ruta ni el fragmento actuales', () {
    final base = Uri.parse('https://app.vivecom.com.mx/alguna/ruta?x=1#/estado');
    expect(base.resolve('/$nombreApk').toString(), 'https://app.vivecom.com.mx/vivecom-android.apk');
    expect(urlDelApk().path, '/$nombreApk');
  });

  Future<void> pumpTarjeta(WidgetTester tester, {bool? visible, AbrirEnlace? abrir}) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DescargarApk(visible: visible, abrir: abrir ?? (_) async {}),
        ),
      ),
    );
  }

  testWidgets('visible: muestra el botón y cómo instalar; al tocarlo abre el APK', (tester) async {
    Uri? abierta;
    await pumpTarjeta(tester, visible: true, abrir: (url) async => abierta = url);

    expect(find.text('¿Usas Android?'), findsOneWidget);
    expect(find.text('Descargar app para Android'), findsOneWidget);
    expect(find.textContaining('Instalar de todos modos'), findsOneWidget);

    await tester.tap(find.byKey(const Key('descargar_apk')));

    expect(abierta!.path, '/vivecom-android.apk');
  });

  testWidgets('no visible: no muestra nada', (tester) async {
    await pumpTarjeta(tester, visible: false);

    expect(find.byKey(const Key('tarjeta_apk')), findsNothing);
    expect(find.byKey(const Key('descargar_apk')), findsNothing);
  });

  testWidgets('sin forzarlo, en la app nativa (o en las pruebas) no se ofrece', (tester) async {
    await pumpTarjeta(tester);

    expect(find.byKey(const Key('tarjeta_apk')), findsNothing);
  });

  testWidgets('el inicio de sesión muestra la tarjeta cuando corresponde y sigue permitiendo entrar', (tester) async {
    SharedPreferences.setMockInitialValues({});
    Uri? abierta;
    var entro = false;
    final auth = AuthService(
      api: ApiClient(
        client: MockClient((r) async => http.Response('{"access_token": "a.b.c", "token_type": "bearer"}', 200)),
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          authService: auth,
          onLoginSuccess: () => entro = true,
          biometricService: _BiometricAuthServiceFalso(),
          instalarApp: InstalarApp(
            apk: DescargarApk(visible: true, abrir: (url) async => abierta = url),
            atajo: const AnadirAPantallaDeInicio(visible: false),
          ),
        ),
      ),
    );

    await tester.ensureVisible(find.byKey(const Key('descargar_apk')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('descargar_apk')));
    expect(abierta!.path, '/vivecom-android.apk');

    await tester.enterText(find.byKey(const Key('email_field')), 'casa1@muestra.vivecom.com.mx');
    await tester.enterText(find.byKey(const Key('password_field')), 'clave-1234');
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Entrar')); // la pantalla se desplaza
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'Entrar'));
    await tester.pumpAndSettle();
    expect(entro, isTrue);
  });
}
