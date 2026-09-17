import '../models/poll.dart';
import 'api_client.dart';

class PollService {
  final ApiClient _api;

  PollService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<List<Poll>> listarVotaciones(String token) async {
    final data = await _api.get('/polls', token: token) as List;
    return data.map((e) => Poll.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> votar(String pollId, String optionId, String token) {
    return _api.post('/polls/$pollId/vote', {'option_id': optionId}, token: token);
  }

  Future<PollResults> obtenerResultados(String pollId, String token) async {
    final data = await _api.get('/polls/$pollId/results', token: token);
    return PollResults.fromJson(data as Map<String, dynamic>);
  }
}
