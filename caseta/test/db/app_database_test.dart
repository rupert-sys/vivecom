import 'dart:typed_data';

import 'package:app_caseta/db/app_database.dart';
import 'package:drift/drift.dart' show Value;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late AppDatabase db;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() => db.close());

  test('un acceso encolado queda pending por default', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()));

    final pendientes = await db.pendientesDeAcceso();
    expect(pendientes, hasLength(1));
    expect(pendientes.first.syncStatus, 'pending');
  });

  test('marcarAccesoSincronizado actualiza el estado y guarda el remoteId', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()));

    await db.marcarAccesoSincronizado('c1', 'remote-1');

    final pendientes = await db.pendientesDeAcceso();
    expect(pendientes, isEmpty); // ya no cuenta como pendiente (isNotValue('synced'))

    final fila = await (db.select(db.pendingAccessLogs)..where((t) => t.clientId.equals('c1'))).getSingle();
    expect(fila.syncStatus, 'synced');
    expect(fila.remoteId, 'remote-1');
  });

  test('marcarAccesoFallido guarda el mensaje de error y no lo cuenta como sincronizado', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()));

    await db.marcarAccesoFallido('c1', 'Conflicto de sincronización');

    final fila = await (db.select(db.pendingAccessLogs)..where((t) => t.clientId.equals('c1'))).getSingle();
    expect(fila.syncStatus, 'failed');
    expect(fila.errorMessage, 'Conflicto de sincronización');
  });

  test('una incidencia encolada queda pending por default y watchIncidencias la refleja', () async {
    await db
        .into(db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(clientId: 'i1', descripcion: 'Fuga de agua', createdAtLocal: DateTime.now()),
        );

    final vistas = await db.watchIncidencias().first;
    expect(vistas, hasLength(1));
    expect(vistas.first.descripcion, 'Fuga de agua');
    expect(vistas.first.syncStatus, 'pending');
  });

  test('marcarIncidenciaSincronizada actualiza el estado', () async {
    await db
        .into(db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(clientId: 'i1', descripcion: 'Fuga de agua', createdAtLocal: DateTime.now()),
        );

    await db.marcarIncidenciaSincronizada('i1', 'remote-i1');

    final pendientes = await db.pendientesDeIncidencia();
    expect(pendientes, isEmpty);
  });

  test('un acceso encolado sin datos extra queda con 0 acompañantes y sin nombre', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'residente', createdAtLocal: DateTime.now()));

    final fila = (await db.pendientesDeAcceso()).single;
    expect(fila.acompanantes, 0);
    expect(fila.nombreVisitante, isNull);
    expect(fila.autorizadoPor, isNull);
  });

  test('una incidencia encolada sin tipo queda de seguridad', () async {
    await db
        .into(db.pendingIncidents)
        .insert(PendingIncidentsCompanion.insert(clientId: 'i1', descripcion: 'Ruido', createdAtLocal: DateTime.now()));

    expect((await db.pendientesDeIncidencia()).single.tipo, 'seguridad');
  });

  test('un paquete encolado queda pending y marcarPaqueteSincronizado lo saca de los pendientes', () async {
    await db
        .into(db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));
    expect((await db.pendientesDePaquete()).single.syncStatus, 'pending');

    await db.marcarPaqueteSincronizado('k1', 'remote-k1');

    expect(await db.pendientesDePaquete(), isEmpty);
    expect((await db.select(db.pendingPackages).getSingle()).remoteId, 'remote-k1');
  });

  test('marcarPaqueteFallido conserva el mensaje del conflicto', () async {
    await db
        .into(db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));

    await db.marcarPaqueteFallido('k1', 'Conflicto');

    final fila = await db.select(db.pendingPackages).getSingle();
    expect((fila.syncStatus, fila.errorMessage), ('failed', 'Conflicto'));
  });

  test('actualizar desde la v1 conserva la cola pendiente y agrega lo nuevo', () async {
    // Un guardia con la app ya instalada tiene la base v1 (con registros sin
    // sincronizar): al actualizar no puede perder su cola.
    final v1 = AppDatabase.forTesting(
      NativeDatabase.memory(
        setup: (raw) {
          raw.execute(
            'CREATE TABLE pending_access_logs (client_id TEXT NOT NULL PRIMARY KEY, property_id TEXT, tipo TEXT NOT NULL, '
            "placas TEXT NOT NULL DEFAULT '[]', created_at_local INTEGER NOT NULL, sync_status TEXT NOT NULL DEFAULT 'pending', "
            'error_message TEXT, remote_id TEXT)',
          );
          raw.execute(
            'CREATE TABLE pending_incidents (client_id TEXT NOT NULL PRIMARY KEY, descripcion TEXT NOT NULL, foto_url TEXT, '
            "created_at_local INTEGER NOT NULL, sync_status TEXT NOT NULL DEFAULT 'pending', error_message TEXT, remote_id TEXT)",
          );
          raw.execute(
            "INSERT INTO pending_access_logs (client_id, tipo, created_at_local) VALUES ('viejo', 'visitante', 1700000000)",
          );
          raw.execute(
            "INSERT INTO pending_incidents (client_id, descripcion, created_at_local) VALUES ('i-viejo', 'Fuga', 1700000000)",
          );
          raw.execute('PRAGMA user_version = 1');
        },
      ),
    );
    addTearDown(v1.close);

    final acceso = (await v1.pendientesDeAcceso()).single;
    expect(acceso.clientId, 'viejo');
    expect(acceso.acompanantes, 0);
    expect(acceso.nombreVisitante, isNull);
    final incidencia = (await v1.pendientesDeIncidencia()).single;
    expect(incidencia.tipo, 'seguridad');
    expect(incidencia.propertyId, isNull);
    expect(incidencia.fotoBytes, isNull);
    expect(incidencia.fotoDescartada, isFalse);
    // la tabla de paquetes existe y funciona
    await v1
        .into(v1.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: 'k1', propertyId: 'p1', createdAtLocal: DateTime.now()));
    expect(await v1.pendientesDePaquete(), hasLength(1));
  });

  test('actualizar desde la v2 conserva las incidencias pendientes y agrega las columnas de la foto', () async {
    final v2 = AppDatabase.forTesting(
      NativeDatabase.memory(
        setup: (raw) {
          raw.execute(
            'CREATE TABLE pending_incidents (client_id TEXT NOT NULL PRIMARY KEY, descripcion TEXT NOT NULL, foto_url TEXT, '
            "tipo TEXT NOT NULL DEFAULT 'seguridad', property_id TEXT, persona_involucrada TEXT, "
            "created_at_local INTEGER NOT NULL, sync_status TEXT NOT NULL DEFAULT 'pending', error_message TEXT, remote_id TEXT)",
          );
          raw.execute(
            "INSERT INTO pending_incidents (client_id, descripcion, tipo, created_at_local) VALUES ('i2', 'Luminaria', 'mantenimiento', 1700000000)",
          );
          raw.execute('PRAGMA user_version = 2');
        },
      ),
    );
    addTearDown(v2.close);

    final incidencia = (await v2.pendientesDeIncidencia()).single;
    expect((incidencia.descripcion, incidencia.tipo), ('Luminaria', 'mantenimiento'));
    expect((incidencia.fotoBytes, incidencia.fotoNombre, incidencia.fotoArchivoId), (null, null, null));
    expect(incidencia.fotoDescartada, isFalse);
  });

  test('una incidencia con foto la guarda en la cola y sincronizarla borra los bytes del teléfono', () async {
    await db
        .into(db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(
            clientId: 'i1',
            descripcion: 'Fuga',
            fotoBytes: Value(Uint8List.fromList([1, 2, 3])),
            fotoNombre: const Value('foto.jpg'),
            createdAtLocal: DateTime.now(),
          ),
        );
    expect((await db.pendientesDeIncidencia()).single.fotoBytes, [1, 2, 3]);

    await db.guardarFotoSubida('i1', 'arch-1');
    expect((await db.pendientesDeIncidencia()).single.fotoArchivoId, 'arch-1');

    await db.marcarIncidenciaSincronizada('i1', 'remote-1');
    final fila = await db.select(db.pendingIncidents).getSingle();
    expect(fila.fotoBytes, isNull); // ya está en el servidor
    expect(fila.fotoArchivoId, 'arch-1');
  });

  test('descartarFoto borra los bytes y lo deja anotado, sin tocar la incidencia', () async {
    await db
        .into(db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(
            clientId: 'i1',
            descripcion: 'Fuga',
            fotoBytes: Value(Uint8List.fromList([9])),
            createdAtLocal: DateTime.now(),
          ),
        );

    await db.descartarFoto('i1');

    final fila = await db.select(db.pendingIncidents).getSingle();
    expect((fila.fotoBytes, fila.fotoDescartada, fila.syncStatus), (null, true, 'pending'));
  });
}
