import '../models/access_log_entry.dart';
import '../models/parking_status.dart';
import 'api_client.dart';

class AccessLogService {
  final ApiClient _api;

  AccessLogService({ApiClient? api}) : _api = api ?? ApiClient();

  // La salida (F2-08) actúa sobre un registro que YA existe del lado del
  // servidor (necesita su id remoto), así que a diferencia de la entrada no
  // se encola offline — requiere conexión. La entrada es el caso crítico de
  // "captura rápida sin conexión" que pide F2-07; la salida típicamente
  // ocurre minutos/horas después, cuando la conexión ya volvió.
  Future<List<AccessLogEntry>> listarAbiertos(String token) async {
    final data = await _api.get('/access-log', token: token) as List;
    return data.map((e) => AccessLogEntry.fromJson(e as Map<String, dynamic>)).where((a) => a.horaSalida == null).toList();
  }

  Future<ParkingStatus> obtenerEstacionamiento(String token) async {
    final data = await _api.get('/access-log/estacionamiento-visitas', token: token);
    return ParkingStatus.fromJson(data as Map<String, dynamic>);
  }

  Future<void> registrarSalida(String accessLogId, String token) {
    return _api.post('/access-log/$accessLogId/exit', {}, token: token);
  }
}
