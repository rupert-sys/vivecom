import 'package:local_auth/local_auth.dart';

// Envuelve el plugin local_auth (Face ID en iPhone, huella/rostro en Android) — nunca se usa directo en una
// pantalla, para poder sustituirlo por un doble de prueba sin depender del canal de plataforma real (que no
// corre en `flutter test`). No reemplaza el login: solo desbloquea una sesión que YA existe (ver AuthService),
// igual que el código de acceso de cualquier app de banco.
class BiometricAuthService {
  final LocalAuthentication _auth;

  BiometricAuthService({LocalAuthentication? auth}) : _auth = auth ?? LocalAuthentication();

  // false si el equipo no tiene biométricos configurados (o no soporta) — no tiene sentido ofrecer la opción.
  // Con límite de tiempo (a diferencia de autenticar(), donde SÍ es normal tardar: un humano respondiendo a
  // Face ID) — esto es solo una consulta de capacidad del equipo, nunca debería demorar; sin el límite, un
  // canal de plataforma que no responde (visto en pruebas de widget sin el plugin real montado) cuelga el
  // login entero esperando una respuesta que nunca llega.
  Future<bool> estaDisponible() async {
    try {
      final soportado = await _auth.isDeviceSupported().timeout(const Duration(seconds: 3));
      final puedeChecar = await _auth.canCheckBiometrics.timeout(const Duration(seconds: 3));
      return soportado && puedeChecar;
    } catch (_) {
      return false;
    }
  }

  // true si el residente pasó la verificación biométrica; false si canceló o falló (nunca lanza por un
  // rechazo — sí por un problema real del plugin, ej. plataforma no soportada en pruebas de widget).
  Future<bool> autenticar(String razon) async {
    try {
      return await _auth.authenticate(
        localizedReason: razon,
        options: const AuthenticationOptions(biometricOnly: true, stickyAuth: true),
      );
    } catch (_) {
      return false;
    }
  }
}
