import '../models/visit.dart';
import 'api_client.dart';

class VisitService {
  final ApiClient _api;

  VisitService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<VisitorQr> generarCodigoDeVisita(String token) async {
    final data = await _api.post('/visitor-qr', {}, token: token);
    return VisitorQr.fromJson(data as Map<String, dynamic>);
  }

  Future<List<VisitorQr>> listarMisCodigos(String token) async {
    final data = await _api.get('/visitor-qr', token: token) as List;
    return data.map((e) => VisitorQr.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<PackageItem>> listarMisPaquetes(String token) async {
    final data = await _api.get('/packages/mine', token: token) as List;
    return data.map((e) => PackageItem.fromJson(e as Map<String, dynamic>)).toList();
  }
}
