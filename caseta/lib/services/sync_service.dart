import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';

import '../db/app_database.dart';
import 'api_client.dart';

// F2-07: SyncService drena la cola local (PendingAccessLogs/PendingIncidents)
// hacia el backend. No confía únicamente en ConnectivityPlus para saber si
// "hay internet real" — esa señal solo dice si hay una interfaz de red
// activa (wifi/datos), no si el backend es alcanzable — así que además de
// reintentar en cada cambio de conectividad, se reintenta con un timer
// periódico de respaldo, y cada intento de sync maneja su propio error de
// red sin tumbar a los demás pendientes.
class SyncService {
  final AppDatabase _db;
  final ApiClient _api;
  final String Function() _obtenerToken;
  final Connectivity _connectivity;

  StreamSubscription<List<ConnectivityResult>>? _conexionSub;
  Timer? _timerRespaldo;
  bool _sincronizando = false;

  SyncService({
    required AppDatabase db,
    required String Function() obtenerToken,
    ApiClient? api,
    Connectivity? connectivity,
  }) : _db = db,
       _obtenerToken = obtenerToken,
       _api = api ?? ApiClient(),
       _connectivity = connectivity ?? Connectivity();

  void iniciar() {
    _conexionSub = _connectivity.onConnectivityChanged.listen((_) => sincronizarPendientes());
    _timerRespaldo = Timer.periodic(const Duration(seconds: 30), (_) => sincronizarPendientes());
    sincronizarPendientes();
  }

  void detener() {
    _conexionSub?.cancel();
    _timerRespaldo?.cancel();
  }

  Future<void> sincronizarPendientes() async {
    if (_sincronizando) return; // evita que dos disparos (timer + conectividad) se pisen
    final token = _obtenerToken();
    if (token.isEmpty) return;

    _sincronizando = true;
    try {
      await _sincronizarAccesos(token);
      await _sincronizarIncidencias(token);
      await _sincronizarPaquetes(token);
    } finally {
      _sincronizando = false;
    }
  }

  Future<void> _sincronizarAccesos(String token) async {
    final pendientes = await _db.pendientesDeAcceso();
    for (final acceso in pendientes.where((a) => a.syncStatus == 'pending')) {
      try {
        final placas = (jsonDecode(acceso.placas) as List).cast<String>();
        final data = await _api.post('/access-log', {
          'client_id': acceso.clientId,
          'property_id': acceso.propertyId,
          'tipo': acceso.tipo,
          'placas': placas,
          if (acceso.nombreVisitante != null) 'nombre_visitante': acceso.nombreVisitante,
          'acompanantes': acceso.acompanantes,
          if (acceso.identificacion != null) 'identificacion': acceso.identificacion,
          if (acceso.autorizadoPor != null) 'autorizado_por': acceso.autorizadoPor,
        }, token: token);
        await _db.marcarAccesoSincronizado(acceso.clientId, data['id'] as String);
      } on ApiException catch (err) {
        // 409: un conflicto real detectado por el backend (mismo client_id,
        // payload distinto) — el backend ya alertó al admin (F2-11); acá solo
        // se conserva el error para mostrarlo en la UI, no tiene caso reintentar.
        if (err.statusCode == 409) {
          await _db.marcarAccesoFallido(acceso.clientId, err.message);
        }
        // Cualquier otro error (sin red, 5xx, etc.) se deja "pending" para
        // reintentar en el siguiente ciclo — no se marca como fallido.
      } catch (_) {
        // Error de red (sin conexión real pese a lo que decía ConnectivityPlus):
        // se deja pending, se reintenta en el siguiente ciclo.
      }
    }
  }

  // Al sincronizar la llegada de un paquete, el backend lo registra; el aviso al
  // residente (app + WhatsApp/SMS) lo manda un barrido periódico del servidor
  // (F2-04) — aquí se pide de inmediato para que no espere a ese ciclo. Si ese
  // disparo falla no importa: el barrido periódico lo cubre igual.
  Future<void> _sincronizarPaquetes(String token) async {
    final pendientes = await _db.pendientesDePaquete();
    var sincronizados = 0;
    for (final paquete in pendientes.where((p) => p.syncStatus == 'pending')) {
      try {
        final data = await _api.post('/packages', {
          'client_id': paquete.clientId,
          'property_id': paquete.propertyId,
        }, token: token);
        await _db.marcarPaqueteSincronizado(paquete.clientId, data['id'] as String);
        sincronizados++;
      } on ApiException catch (err) {
        if (err.statusCode == 409) {
          await _db.marcarPaqueteFallido(paquete.clientId, err.message);
        }
      } catch (_) {
        // Error de red: se deja pending.
      }
    }
    if (sincronizados > 0) {
      try {
        await _api.post('/packages/send-notifications', {}, token: token);
      } catch (_) {
        // El barrido periódico del servidor avisa de todos modos.
      }
    }
  }

  Future<void> _sincronizarIncidencias(String token) async {
    final pendientes = await _db.pendientesDeIncidencia();
    for (final incidencia in pendientes.where((i) => i.syncStatus == 'pending')) {
      try {
        final data = await _api.post('/incidents', {
          'client_id': incidencia.clientId,
          'descripcion': incidencia.descripcion,
          'tipo': incidencia.tipo,
          if (incidencia.propertyId != null) 'property_id': incidencia.propertyId,
          if (incidencia.personaInvolucrada != null) 'persona_involucrada': incidencia.personaInvolucrada,
          if (incidencia.fotoUrl != null) 'foto_url': incidencia.fotoUrl,
        }, token: token);
        await _db.marcarIncidenciaSincronizada(incidencia.clientId, data['id'] as String);
      } on ApiException catch (err) {
        if (err.statusCode == 409) {
          await _db.marcarIncidenciaFallida(incidencia.clientId, err.message);
        }
      } catch (_) {
        // Error de red: se deja pending.
      }
    }
  }
}
