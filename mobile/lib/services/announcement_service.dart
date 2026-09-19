import '../models/announcement.dart';
import '../models/announcement_question.dart';
import 'api_client.dart';

class AnnouncementService {
  final ApiClient _api;

  AnnouncementService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<List<Announcement>> listarAvisos(String token) async {
    final data = await _api.get('/announcements', token: token) as List;
    return data.map((e) => Announcement.fromJson(e as Map<String, dynamic>)).toList();
  }

  // Las dudas de un aviso: las de MI vivienda y las aclaraciones que la administración publicó.
  Future<List<AnnouncementQuestion>> listarDudas(String announcementId, String token) async {
    final data = await _api.get('/announcements/$announcementId/questions', token: token) as List;
    return data.map((e) => AnnouncementQuestion.fromJson(e as Map<String, dynamic>)).toList();
  }

  // Tope de 3 sin responder por vivienda y aviso; el backend explica el rechazo (ApiException).
  Future<AnnouncementQuestion> preguntar(String announcementId, String texto, String token) async {
    final data = await _api.post('/announcements/$announcementId/questions', {'texto': texto.trim()}, token: token);
    return AnnouncementQuestion.fromJson(data as Map<String, dynamic>);
  }

  Future<List<AnnouncementQuestion>> listarMisDudas(String token) async {
    final data = await _api.get('/announcement-questions/mine', token: token) as List;
    return data.map((e) => AnnouncementQuestion.fromJson(e as Map<String, dynamic>)).toList();
  }

  // El residente ya vio las respuestas de este aviso: dejan de marcarse como nuevas.
  Future<void> marcarRespuestasVistas(String announcementId, String token) {
    return _api.post('/announcement-questions/mine/seen?announcement_id=$announcementId', {}, token: token);
  }

  Future<void> marcarLeido(String announcementId, String token) {
    return _api.post('/announcements/$announcementId/read', {}, token: token);
  }
}
