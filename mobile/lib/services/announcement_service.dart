import '../models/announcement.dart';
import 'api_client.dart';

class AnnouncementService {
  final ApiClient _api;

  AnnouncementService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<List<Announcement>> listarAvisos(String token) async {
    final data = await _api.get('/announcements', token: token) as List;
    return data.map((e) => Announcement.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> marcarLeido(String announcementId, String token) {
    return _api.post('/announcements/$announcementId/read', {}, token: token);
  }
}
