import '../models/package_entry.dart';
import 'api_client.dart';

class PackageService {
  final ApiClient _api;

  PackageService({ApiClient? api}) : _api = api ?? ApiClient();

  // Los paquetes que siguen en la caseta. Como la salida de un acceso, la
  // entrega actúa sobre un registro que ya existe en el servidor: requiere
  // conexión (la llegada, en cambio, se encola offline).
  Future<List<PackageEntry>> listarEnCaseta(String token) async {
    final data = await _api.get('/packages?pendientes=true', token: token) as List;
    return data.map((e) => PackageEntry.fromJson(e as Map<String, dynamic>)).toList();
  }

  // Al entregarse, el backend cierra el registro y avisa al residente que ya lo recogió.
  Future<void> marcarEntregado(String packageId, String token) {
    return _api.post('/packages/$packageId/pickup', {}, token: token);
  }
}
