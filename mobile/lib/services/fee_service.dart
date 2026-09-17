import '../models/fee.dart';
import 'api_client.dart';

class FeeService {
  final ApiClient _api;

  FeeService({ApiClient? api}) : _api = api ?? ApiClient();

  // GET /fees regresa TODAS las cuotas ordenadas por activa_desde DESC (ver
  // list_fees en el backend) — la primera cuya activa_desde ya pasó es la
  // vigente, mismo criterio que get_active_fee() en fee_charge_service.py.
  Future<Fee?> obtenerCuotaVigente(String token) async {
    final data = await _api.get('/fees', token: token) as List;
    final cuotas = data.map((e) => Fee.fromJson(e as Map<String, dynamic>)).toList();
    final ahora = DateTime.now();
    for (final cuota in cuotas) {
      if (!cuota.activaDesde.isAfter(ahora)) {
        return cuota;
      }
    }
    return null;
  }
}
