import 'package:app_residente/screens/bloqueo_biometrico_screen.dart';
import 'package:app_residente/services/biometric_auth_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// Doble de prueba: BiometricAuthService envuelve el plugin local_auth (canal de plataforma, no corre en
// `flutter test`) — se sustituye por esta subclase en vez de tocar el plugin real.
class _BiometricAuthServiceFalso extends BiometricAuthService {
  final bool resultado;
  String? razonRecibida;
  int llamadas = 0;

  _BiometricAuthServiceFalso({required this.resultado});

  @override
  Future<bool> autenticar(String razon) async {
    llamadas++;
    razonRecibida = razon;
    return resultado;
  }
}

void main() {
  testWidgets('pide la verificación biométrica al abrirse, y si tiene éxito llama a onDesbloqueado', (tester) async {
    final biometrico = _BiometricAuthServiceFalso(resultado: true);
    var desbloqueado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: BloqueoBiometricoScreen(
          biometricService: biometrico,
          onDesbloqueado: () => desbloqueado = true,
          onCerrarSesion: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(biometrico.llamadas, 1);
    expect(biometrico.razonRecibida, isNotEmpty);
    expect(desbloqueado, isTrue);
  });

  testWidgets('si falla, muestra el error y un botón para reintentar en vez de desbloquear', (tester) async {
    final biometrico = _BiometricAuthServiceFalso(resultado: false);
    var desbloqueado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: BloqueoBiometricoScreen(
          biometricService: biometrico,
          onDesbloqueado: () => desbloqueado = true,
          onCerrarSesion: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(desbloqueado, isFalse);
    expect(find.text('No se pudo confirmar tu identidad.'), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Intentar de nuevo'), findsOneWidget);

    await tester.tap(find.widgetWithText(ElevatedButton, 'Intentar de nuevo'));
    await tester.pumpAndSettle();

    expect(biometrico.llamadas, 2);
  });

  testWidgets('"Cerrar sesión" llama a onCerrarSesion sin necesidad de pasar el biométrico', (tester) async {
    final biometrico = _BiometricAuthServiceFalso(resultado: false);
    var cerrado = false;

    await tester.pumpWidget(
      MaterialApp(
        home: BloqueoBiometricoScreen(
          biometricService: biometrico,
          onDesbloqueado: () {},
          onCerrarSesion: () => cerrado = true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(TextButton, 'Cerrar sesión'));
    await tester.pumpAndSettle();

    expect(cerrado, isTrue);
  });
}
