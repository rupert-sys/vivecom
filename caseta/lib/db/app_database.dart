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
  // Reglamento Art. 17 V: la bitácora lleva nombre, acompañantes, identificación
  // y quién autorizó el acceso.
  TextColumn get nombreVisitante => text().nullable()();
  IntColumn get acompanantes => integer().withDefault(const Constant(0))();
  TextColumn get identificacion => text().nullable()();
  TextColumn get autorizadoPor => text().nullable()(); // residente_previo | telefono | otro
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
  // seguridad | mantenimiento | otro — la caseta reporta fallas de mantenimiento
  // además de incidentes de seguridad.
  TextColumn get tipo => text().withDefault(const Constant('seguridad'))();
  TextColumn get propertyId => text().nullable()(); // casa involucrada
  TextColumn get personaInvolucrada => text().nullable()();
  // Foto de la incidencia, guardada AQUÍ mientras no hay conexión: al sincronizar se sube primero
  // el archivo (POST /files, kind=incidencia) y la incidencia lleva su id. Ya subida, fotoArchivoId
  // evita subirla de nuevo en un reintento, y los bytes se borran para no llenar el teléfono.
  BlobColumn get fotoBytes => blob().nullable()();
  TextColumn get fotoNombre => text().nullable()();
  TextColumn get fotoArchivoId => text().nullable()();
  // El servidor no aceptó la foto (tipo o peso inválidos): la incidencia se manda igual, sin ella.
  BoolColumn get fotoDescartada => boolean().withDefault(const Constant(false))();
  DateTimeColumn get createdAtLocal => dateTime()();
  TextColumn get syncStatus => text().withDefault(const Constant('pending'))();
  TextColumn get errorMessage => text().nullable()();
  TextColumn get remoteId => text().nullable()();

  @override
  Set<Column> get primaryKey => {clientId};
}

// Llegada de un paquete registrada por el guardia. Se encola igual que un
// acceso: capturarla es lo crítico y no puede depender de tener red; al
// sincronizar, el backend avisa al residente (F2-04).
class PendingPackages extends Table {
  TextColumn get clientId => text()();
  TextColumn get propertyId => text()();
  DateTimeColumn get createdAtLocal => dateTime()();
  TextColumn get syncStatus => text().withDefault(const Constant('pending'))();
  TextColumn get errorMessage => text().nullable()();
  TextColumn get remoteId => text().nullable()();

  @override
  Set<Column> get primaryKey => {clientId};
}

@DriftDatabase(tables: [PendingAccessLogs, PendingIncidents, PendingPackages])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_abrirConexion());
  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 3;

  // v2 (reglamento) y v3 (foto de incidencias): datos extra de la bitácora de acceso, tipo/casa/persona de
  // las incidencias y la cola de paquetes. Un dispositivo que ya tenía la app
  // instalada conserva su cola pendiente al actualizar.
  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) => m.createAll(),
    onUpgrade: (m, from, to) async {
      if (from < 2) {
        await m.addColumn(pendingAccessLogs, pendingAccessLogs.nombreVisitante);
        await m.addColumn(pendingAccessLogs, pendingAccessLogs.acompanantes);
        await m.addColumn(pendingAccessLogs, pendingAccessLogs.identificacion);
        await m.addColumn(pendingAccessLogs, pendingAccessLogs.autorizadoPor);
        await m.addColumn(pendingIncidents, pendingIncidents.tipo);
        await m.addColumn(pendingIncidents, pendingIncidents.propertyId);
        await m.addColumn(pendingIncidents, pendingIncidents.personaInvolucrada);
        await m.createTable(pendingPackages);
      }
      // v3: foto de la incidencia.
      if (from < 3) {
        await m.addColumn(pendingIncidents, pendingIncidents.fotoBytes);
        await m.addColumn(pendingIncidents, pendingIncidents.fotoNombre);
        await m.addColumn(pendingIncidents, pendingIncidents.fotoArchivoId);
        await m.addColumn(pendingIncidents, pendingIncidents.fotoDescartada);
      }
    },
  );

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

  Future<List<PendingPackage>> pendientesDePaquete() =>
      (select(pendingPackages)..where((t) => t.syncStatus.isNotValue('synced'))).get();

  Stream<List<PendingPackage>> watchPaquetes() =>
      (select(pendingPackages)..orderBy([(t) => OrderingTerm.desc(t.createdAtLocal)])).watch();

  Future<void> marcarPaqueteSincronizado(String clientId, String remoteId) =>
      (update(pendingPackages)..where((t) => t.clientId.equals(clientId)))
          .write(PendingPackagesCompanion(syncStatus: const Value('synced'), remoteId: Value(remoteId), errorMessage: const Value(null)));

  Future<void> marcarPaqueteFallido(String clientId, String error) =>
      (update(pendingPackages)..where((t) => t.clientId.equals(clientId)))
          .write(PendingPackagesCompanion(syncStatus: const Value('failed'), errorMessage: Value(error)));

  Future<void> marcarIncidenciaSincronizada(String clientId, String remoteId) =>
      (update(pendingIncidents)..where((t) => t.clientId.equals(clientId))).write(
        PendingIncidentsCompanion(
          syncStatus: const Value('synced'),
          remoteId: Value(remoteId),
          errorMessage: const Value(null),
          fotoBytes: const Value(null), // ya está en el servidor: no se guarda dos veces en el teléfono
        ),
      );

  // La foto ya se subió: se recuerda su id para que un reintento no la suba otra vez.
  Future<void> guardarFotoSubida(String clientId, String archivoId) =>
      (update(pendingIncidents)..where((t) => t.clientId.equals(clientId)))
          .write(PendingIncidentsCompanion(fotoArchivoId: Value(archivoId)));

  Future<void> descartarFoto(String clientId) =>
      (update(pendingIncidents)..where((t) => t.clientId.equals(clientId)))
          .write(const PendingIncidentsCompanion(fotoBytes: Value(null), fotoDescartada: Value(true)));

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
