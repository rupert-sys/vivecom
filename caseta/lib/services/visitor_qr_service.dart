import '../models/visitor_qr_validation.dart';
import 'api_client.dart';

class VisitorQrService {
  final ApiClient _api;

  VisitorQrService({ApiClient? api}) : _api = api ?? ApiClient();

  // F2-10: valida (y consume) el QR de un solo uso generado por el
  // residente. Requiere conexión — no tiene sentido encolarlo offline, ya
  // que el propio resultado (si el código es válido o ya se usó) solo lo
  // sabe el servidor.
  Future<VisitorQrValidation> validar(String codigo, String token) async {
    final data = await _api.post('/visitor-qr/$codigo/validate', {}, token: token);
    return VisitorQrValidation.fromJson(data as Map<String, dynamic>);
  }
}
