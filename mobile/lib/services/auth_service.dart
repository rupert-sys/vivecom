import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';

class TokenPayload {
  final String sub;
  final String tenantId;
  final String schema;
  final String rol;
  final String? propertyId;

  const TokenPayload({
    required this.sub,
    required this.tenantId,
    required this.schema,
    required this.rol,
    required this.propertyId,
  });

  // Decodificado SOLO para mostrar/ocultar UI según rol — nunca una barrera
  // de seguridad real. El backend sigue siendo quien valida cada rol vía
  // require_roles (mismo criterio que AuthContext.tsx del panel admin web).
  factory TokenPayload.decode(String token) {
    final segmentos = token.split('.');
    final payload = base64Url.normalize(segmentos[1]);
    final mapa = jsonDecode(utf8.decode(base64Url.decode(payload))) as Map<String, dynamic>;
    return TokenPayload(
      sub: mapa['sub'] as String,
      tenantId: mapa['tenant_id'] as String,
      schema: mapa['schema'] as String,
      rol: mapa['rol'] as String,
      propertyId: mapa['property_id'] as String?,
    );
  }
}

class AuthService {
  static const _tokenKey = 'access_token';
  static const _biometricsKey = 'biometrics_enabled';

  final ApiClient _api;

  AuthService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<String?> obtenerToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  Future<void> login(String email, String password) async {
    final data = await _api.post('/auth/login', {'email': email, 'password': password});
    await guardarToken(data['access_token'] as String);
  }

  // Expuesto para quien obtiene un token por otro camino (ej. RegistroScreen, que llama
  // POST /residents/activar directamente — auto-login igual que /signup) y necesita persistirlo
  // con la misma llave que usa el resto de la app.
  Future<void> guardarToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    // Sin sesión que desbloquear, la preferencia de biométricos ya no aplica — se vuelve a ofrecer en el
    // próximo login manual (ver LoginScreen).
    await prefs.remove(_biometricsKey);
  }

  // Face ID/huella para entrar más rápido (ver BiometricAuthService): NO es una segunda credencial — solo
  // desbloquea la sesión que ya existe (BloqueoBiometricoScreen, ver main.dart). Desactivada por defecto: el
  // residente lo activa explícitamente después de un login manual exitoso.
  Future<bool> biometricosActivados() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_biometricsKey) ?? false;
  }

  Future<void> activarBiometricos() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_biometricsKey, true);
  }

  Future<void> desactivarBiometricos() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_biometricsKey);
  }
}
