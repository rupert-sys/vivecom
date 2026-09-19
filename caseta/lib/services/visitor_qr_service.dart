import '../models/visitor_qr_validation.dart';
import 'api_client.dart';

class VisitorQrService {
  final ApiClient _api;

  VisitorQrService({ApiClient? api}) : _api = api ?? ApiClient();

  // F2-10: valida (y consume) el QR de un solo uso generado por el
  // residente. Requiere conexión — no tiene sentido encolarlo offline, ya
  // que el propio resultado (si el código es válido o ya se usó) solo lo
  // sabe el servidor.
  // El guardia emite un código de un solo uso para un proveedor: a una vivienda
  // concreta, o al condominio en general si no se indica (jardinería, mensajería).
  Future<ProviderCode> emitirCodigoProveedor(String descripcion, String? propertyId, String token) async {
    final data = await _api.post('/visitor-qr/provider', {
      'descripcion': descripcion,
      'property_id': ?propertyId,
    }, token: token);
    return ProviderCode.fromJson(data as Map<String, dynamic>);
  }

  Future<VisitorQrValidation> validar(String codigo, String token) async {
    final data = await _api.post('/visitor-qr/$codigo/validate', {}, token: token);
    return VisitorQrValidation.fromJson(data as Map<String, dynamic>);
  }
}
