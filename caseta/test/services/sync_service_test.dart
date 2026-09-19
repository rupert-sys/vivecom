import 'dart:convert';

import 'package:app_caseta/db/app_database.dart';
import 'package:app_caseta/services/api_client.dart';
import 'package:app_caseta/services/sync_service.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  late AppDatabase db;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() => db.close());

  test('sincroniza un acceso pendiente y lo marca synced con el id remoto', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(
            clientId: 'c1',
            propertyId: const Value('p1'),
            tipo: 'visitante',
            placas: const Value('["ABC-123"]'),
            createdAtLocal: DateTime.now(),
          ),
        );

    final mockClient = MockClient((request) async {
      expect(request.url.path, '/access-log');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['client_id'], 'c1');
      expect(body['placas'], ['ABC-123']);
      return http.Response('{"id": "remote-1", "property_id": "p1", "tipo": "visitante", "hora_entrada": "2026-10-01T10:00:00", "hora_salida": null, "placas": ["ABC-123"]}', 201);
    });
    final sync = SyncService(db: db, obtenerToken: () => 'un-token', api: ApiClient(client: mockClient));

    await sync.sincronizarPendientes();

    final pendientes = await db.pendientesDeAcceso();
    expect(pendientes, isEmpty);
    final fila = await (db.select(db.pendingAccessLogs)..where((t) => t.clientId.equals('c1'))).getSingle();
    expect(fila.syncStatus, 'synced');
    expect(fila.remoteId, 'remote-1');
  });

  test('un conflicto (409) marca el registro como failed con el mensaje del backend', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()),
        );

    final mockClient = MockClient((request) async => http.Response('{"detail": "Conflicto de sincronización"}', 409));
    final sync = SyncService(db: db, obtenerToken: () => 'un-token', api: ApiClient(client: mockClient));

    await sync.sincronizarPendientes();

    final fila = await (db.select(db.pendingAccessLogs)..where((t) => t.clientId.equals('c1'))).getSingle();
    expect(fila.syncStatus, 'failed');
    expect(fila.errorMessage, 'Conflicto de sincronización');
  });

  test('un error de red deja el registro pending para reintentar después', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()),
        );

    final mockClient = MockClient((request) async => throw Exception('Failed host lookup'));
    final sync = SyncService(db: db, obtenerToken: () => 'un-token', api: ApiClient(client: mockClient));

    await sync.sincronizarPendientes();

    final fila = await (db.select(db.pendingAccessLogs)..where((t) => t.clientId.equals('c1'))).getSingle();
    expect(fila.syncStatus, 'pending');
  });

  test('sin token no intenta sincronizar nada', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()),
        );

    var llamadas = 0;
    final mockClient = MockClient((request) async {
      llamadas++;
      return http.Response('{}', 201);
    });
    final sync = SyncService(db: db, obtenerToken: () => '', api: ApiClient(client: mockClient));

    await sync.sincronizarPendientes();

    expect(llamadas, 0);
  });

  test('sincroniza también una incidencia pendiente', () async {
    await db
        .into(db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(clientId: 'i1', descripcion: 'Fuga de agua', createdAtLocal: DateTime.now()),
        );

    final mockClient = MockClient((request) async {
      expect(request.url.path, '/incidents');
      return http.Response('{"id": "remote-i1", "reportado_por": "u1", "estado": "abierta", "descripcion": "Fuga de agua", "foto_url": null, "created_at": "2026-10-01T10:00:00", "resolved_at": null}', 201);
    });
    final sync = SyncService(db: db, obtenerToken: () => 'un-token', api: ApiClient(client: mockClient));

    await sync.sincronizarPendientes();

    final fila = await (db.select(db.pendingIncidents)..where((t) => t.clientId.equals('i1'))).getSingle();
    expect(fila.syncStatus, 'synced');
    expect(fila.remoteId, 'remote-i1');
  });

  test('manda al backend nombre, acompañantes, identificación y quién autorizó', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(
            clientId: 'c1',
            tipo: 'visitante',
            nombreVisitante: const Value('Ana López'),
            acompanantes: const Value(2),
            identificacion: const Value('INE 1234'),
            autorizadoPor: const Value('telefono'),
            createdAtLocal: DateTime.now(),
          ),
        );
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response('{"id": "r1"}', 201);
    });

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    expect(cuerpo!['nombre_visitante'], 'Ana López');
    expect(cuerpo!['acompanantes'], 2);
    expect(cuerpo!['identificacion'], 'INE 1234');
    expect(cuerpo!['autorizado_por'], 'telefono');
  });

  test('un acceso sin datos extra no manda campos vacíos', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'residente', createdAtLocal: DateTime.now()));
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response('{"id": "r1"}', 201);
    });

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    expect(cuerpo!.containsKey('nombre_visitante'), isFalse);
    expect(cuerpo!.containsKey('identificacion'), isFalse);
    expect(cuerpo!['acompanantes'], 0);
  });

  test('la incidencia manda su tipo, la casa y la persona involucrada', () async {
    await db
        .into(db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(
            clientId: 'i1',
            descripcion: 'Luminaria fundida',
            tipo: const Value('mantenimiento'),
            propertyId: const Value('p2'),
            personaInvolucrada: const Value('Vecino'),
            createdAtLocal: DateTime.now(),
          ),
        );
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response('{"id": "ri1"}', 201);
    });

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    expect(cuerpo!['tipo'], 'mantenimiento');
    expect(cuerpo!['property_id'], 'p2');
    expect(cuerpo!['persona_involucrada'], 'Vecino');
  });

  test('sincroniza la llegada de un paquete con su client_id y pide avisar al residente', () async {
    await db
        .into(db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));
    final rutas = <String>[];
    Map<String, dynamic>? cuerpo;
    final mockClient = MockClient((request) async {
      rutas.add(request.url.path);
      if (request.url.path == '/packages') {
        cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response('{"id": "rk1", "property_id": "p1"}', 201);
      }
      return http.Response('{"enviadas": 1}', 200);
    });

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    expect(cuerpo, {'client_id': 'k1', 'property_id': 'p1'});
    expect(rutas, ['/packages', '/packages/send-notifications']);
    final fila = await (db.select(db.pendingPackages)..where((t) => t.clientId.equals('k1'))).getSingle();
    expect((fila.syncStatus, fila.remoteId), ('synced', 'rk1'));
  });

  test('si falla el disparo del aviso, el paquete queda sincronizado igual', () async {
    await db
        .into(db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));
    final mockClient = MockClient((request) async {
      if (request.url.path == '/packages') return http.Response('{"id": "rk1"}', 201);
      return http.Response('{"detail": "Twilio caído"}', 500);
    });

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    expect((await db.pendientesDePaquete()), isEmpty);
  });

  test('sin paquetes nuevos no se pide ningún aviso', () async {
    await db
        .into(db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));
    final rutas = <String>[];
    final mockClient = MockClient((request) async {
      rutas.add(request.url.path);
      return http.Response('{"detail": "sin red"}', 503);
    });

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    expect(rutas, ['/packages']); // el paquete sigue pendiente: no hay nada que avisar todavía
    expect((await db.pendientesDePaquete()).single.syncStatus, 'pending');
  });

  test('un conflicto (409) al sincronizar un paquete lo marca como failed', () async {
    await db
        .into(db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));
    final mockClient = MockClient((request) async => http.Response('{"detail": "Conflicto de sincronización"}', 409));

    await SyncService(db: db, obtenerToken: () => 't', api: ApiClient(client: mockClient)).sincronizarPendientes();

    final fila = await db.select(db.pendingPackages).getSingle();
    expect((fila.syncStatus, fila.errorMessage), ('failed', 'Conflicto de sincronización'));
  });
}
