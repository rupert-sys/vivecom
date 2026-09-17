import 'package:app_caseta/db/app_database.dart';
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
        .insert(
          PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()),
        );

    final pendientes = await db.pendientesDeAcceso();
    expect(pendientes, hasLength(1));
    expect(pendientes.first.syncStatus, 'pending');
  });

  test('marcarAccesoSincronizado actualiza el estado y guarda el remoteId', () async {
    await db
        .into(db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()),
        );

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
        .insert(
          PendingAccessLogsCompanion.insert(clientId: 'c1', tipo: 'visitante', createdAtLocal: DateTime.now()),
        );

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
}
