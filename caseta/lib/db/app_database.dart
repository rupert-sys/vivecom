import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqlite3_flutter_libs/sqlite3_flutter_libs.dart';

part 'app_database.g.dart';

// F2-07: cola local de sincronización — un registro de acceso o una
// incidencia capturados sin conexión se guardan aquí primero (syncStatus
// "pending") y SyncService los manda al backend en cuanto hay conexión.
// clientId es el mismo UUID generado en el dispositivo que se manda como
// `client_id` al backend (POST /access-log, POST /incidents) para que un
// reintento de sync no cree un duplicado del lado del servidor (F2-11).
class PendingAccessLogs extends Table {
  TextColumn get clientId => text()();
  TextColumn get propertyId => text().nullable()();
  TextColumn get tipo => text()(); // TipoAcceso: residente | visitante | proveedor
  TextColumn get placas => text().withDefault(const Constant('[]'))(); // JSON list<String>
  DateTimeColumn get createdAtLocal => dateTime()();
  TextColumn get syncStatus => text().withDefault(const Constant('pending'))(); // pending | synced | failed
  TextColumn get errorMessage => text().nullable()();
  TextColumn get remoteId => text().nullable()();

  @override
  Set<Column> get primaryKey => {clientId};
}

class PendingIncidents extends Table {
  TextColumn get clientId => text()();
  TextColumn get descripcion => text()();
  TextColumn get fotoUrl => text().nullable()();
  DateTimeColumn get createdAtLocal => dateTime()();
  TextColumn get syncStatus => text().withDefault(const Constant('pending'))();
  TextColumn get errorMessage => text().nullable()();
  TextColumn get remoteId => text().nullable()();

  @override
  Set<Column> get primaryKey => {clientId};
}

@DriftDatabase(tables: [PendingAccessLogs, PendingIncidents])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_abrirConexion());
  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 1;

  Future<List<PendingAccessLog>> pendientesDeAcceso() =>
      (select(pendingAccessLogs)..where((t) => t.syncStatus.isNotValue('synced'))).get();

  Future<List<PendingIncident>> pendientesDeIncidencia() =>
      (select(pendingIncidents)..where((t) => t.syncStatus.isNotValue('synced'))).get();

  Stream<List<PendingAccessLog>> watchAccesos() =>
      (select(pendingAccessLogs)..orderBy([(t) => OrderingTerm.desc(t.createdAtLocal)])).watch();

  Stream<List<PendingIncident>> watchIncidencias() =>
      (select(pendingIncidents)..orderBy([(t) => OrderingTerm.desc(t.createdAtLocal)])).watch();

  Future<void> marcarAccesoSincronizado(String clientId, String remoteId) =>
      (update(pendingAccessLogs)..where((t) => t.clientId.equals(clientId)))
          .write(PendingAccessLogsCompanion(syncStatus: const Value('synced'), remoteId: Value(remoteId), errorMessage: const Value(null)));

  Future<void> marcarAccesoFallido(String clientId, String error) =>
      (update(pendingAccessLogs)..where((t) => t.clientId.equals(clientId)))
          .write(PendingAccessLogsCompanion(syncStatus: const Value('failed'), errorMessage: Value(error)));

  Future<void> marcarIncidenciaSincronizada(String clientId, String remoteId) =>
      (update(pendingIncidents)..where((t) => t.clientId.equals(clientId)))
          .write(PendingIncidentsCompanion(syncStatus: const Value('synced'), remoteId: Value(remoteId), errorMessage: const Value(null)));

  Future<void> marcarIncidenciaFallida(String clientId, String error) =>
      (update(pendingIncidents)..where((t) => t.clientId.equals(clientId)))
          .write(PendingIncidentsCompanion(syncStatus: const Value('failed'), errorMessage: Value(error)));
}

QueryExecutor _abrirConexion() {
  return LazyDatabase(() async {
    await applyWorkaroundToOpenSqlite3OnOldAndroidVersions();
    final dir = await getApplicationDocumentsDirectory();
    final file = File(p.join(dir.path, 'caseta.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
