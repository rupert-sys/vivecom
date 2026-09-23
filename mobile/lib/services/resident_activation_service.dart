import '../models/resident_activation_preview.dart';
import 'api_client.dart';

// Ambos endpoints son públicos (como /auth/login): un residente todavía no tiene token cuando se registra.
// Ver app/api/residents.py (preview_activacion, activar_residente) y ResidentActivationRequest.
class ResidentActivationService {
  final ApiClient _api;

  ResidentActivationService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<ResidentActivationPreview> preview({required String nombreCondominio, required int numeroDeCasa}) async {
    final query = Uri(queryParameters: {
      'nombre_condominio': nombreCondominio,
      'numero_de_casa': numeroDeCasa.toString(),
    }).query;
    final data = await _api.get('/residents/activar/preview?$query');
    return ResidentActivationPreview.fromJson(data as Map<String, dynamic>);
  }

  // Regresa el access_token (auto-login, igual que /signup para el admin) — quien llama decide cómo
  // guardarlo (ver AuthService.guardarToken).
  Future<String> activar({
    required String nombreCondominio,
    required int numeroDeCasa,
    required String nombreCompleto,
    required String rol, // "propietario" | "inquilino"
    required String telefono,
    required String password,
  }) async {
    final data = await _api.post('/residents/activar', {
      'nombre_condominio': nombreCondominio,
      'numero_de_casa': numeroDeCasa,
      'nombre_completo': nombreCompleto,
      'rol': rol,
      'telefono': telefono,
      'password': password,
    });
    return data['access_token'] as String;
  }
}
