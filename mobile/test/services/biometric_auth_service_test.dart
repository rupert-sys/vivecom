import 'package:app_residente/services/biometric_auth_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // Sin un canal de plataforma real (no corre en `flutter test`, solo en un dispositivo/simulador), el plugin
  // local_auth lanza MissingPluginException al primer método que se le llame — BiometricAuthService debe
  // degradarse a "no disponible"/"no autenticado" en vez de dejar que la excepción tumbe la pantalla que lo usa.
  test('estaDisponible no truena si el plugin no tiene canal de plataforma: regresa false', () async {
    final service = BiometricAuthService();

    expect(await service.estaDisponible(), isFalse);
  });

  test('autenticar no truena si el plugin no tiene canal de plataforma: regresa false', () async {
    final service = BiometricAuthService();

    expect(await service.autenticar('Confirma tu identidad'), isFalse);
  });
}
