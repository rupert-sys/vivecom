import '../models/lost_found_item.dart';
import 'api_client.dart';

class LostFoundService {
  final ApiClient _api;

  LostFoundService({ApiClient? api}) : _api = api ?? ApiClient();

  // GET /lost-found (F2-15) le regresa a un residente solo lo ya autorizado
  // — el backend filtra, no hace falta filtrar de nuevo aquí.
  Future<List<LostFoundItem>> listarObjetos(String token) async {
    final data = await _api.get('/lost-found', token: token) as List;
    return data.map((e) => LostFoundItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<LostFoundItem> publicarObjeto(String descripcion, String? fotoUrl, String token) async {
    final data = await _api.post(
      '/lost-found',
      {'descripcion': descripcion, if (fotoUrl != null && fotoUrl.isNotEmpty) 'foto_url': fotoUrl},
      token: token,
    );
    return LostFoundItem.fromJson(data as Map<String, dynamic>);
  }
}
