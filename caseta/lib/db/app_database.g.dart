// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $PendingAccessLogsTable extends PendingAccessLogs
    with TableInfo<$PendingAccessLogsTable, PendingAccessLog> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PendingAccessLogsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _clientIdMeta = const VerificationMeta(
    'clientId',
  );
  @override
  late final GeneratedColumn<String> clientId = GeneratedColumn<String>(
    'client_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _propertyIdMeta = const VerificationMeta(
    'propertyId',
  );
  @override
  late final GeneratedColumn<String> propertyId = GeneratedColumn<String>(
    'property_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _tipoMeta = const VerificationMeta('tipo');
  @override
  late final GeneratedColumn<String> tipo = GeneratedColumn<String>(
    'tipo',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _placasMeta = const VerificationMeta('placas');
  @override
  late final GeneratedColumn<String> placas = GeneratedColumn<String>(
    'placas',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('[]'),
  );
  static const VerificationMeta _createdAtLocalMeta = const VerificationMeta(
    'createdAtLocal',
  );
  @override
  late final GeneratedColumn<DateTime> createdAtLocal =
      GeneratedColumn<DateTime>(
        'created_at_local',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _syncStatusMeta = const VerificationMeta(
    'syncStatus',
  );
  @override
  late final GeneratedColumn<String> syncStatus = GeneratedColumn<String>(
    'sync_status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('pending'),
  );
  static const VerificationMeta _errorMessageMeta = const VerificationMeta(
    'errorMessage',
  );
  @override
  late final GeneratedColumn<String> errorMessage = GeneratedColumn<String>(
    'error_message',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _remoteIdMeta = const VerificationMeta(
    'remoteId',
  );
  @override
  late final GeneratedColumn<String> remoteId = GeneratedColumn<String>(
    'remote_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    clientId,
    propertyId,
    tipo,
    placas,
    createdAtLocal,
    syncStatus,
    errorMessage,
    remoteId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pending_access_logs';
  @override
  VerificationContext validateIntegrity(
    Insertable<PendingAccessLog> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('client_id')) {
      context.handle(
        _clientIdMeta,
        clientId.isAcceptableOrUnknown(data['client_id']!, _clientIdMeta),
      );
    } else if (isInserting) {
      context.missing(_clientIdMeta);
    }
    if (data.containsKey('property_id')) {
      context.handle(
        _propertyIdMeta,
        propertyId.isAcceptableOrUnknown(data['property_id']!, _propertyIdMeta),
      );
    }
    if (data.containsKey('tipo')) {
      context.handle(
        _tipoMeta,
        tipo.isAcceptableOrUnknown(data['tipo']!, _tipoMeta),
      );
    } else if (isInserting) {
      context.missing(_tipoMeta);
    }
    if (data.containsKey('placas')) {
      context.handle(
        _placasMeta,
        placas.isAcceptableOrUnknown(data['placas']!, _placasMeta),
      );
    }
    if (data.containsKey('created_at_local')) {
      context.handle(
        _createdAtLocalMeta,
        createdAtLocal.isAcceptableOrUnknown(
          data['created_at_local']!,
          _createdAtLocalMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_createdAtLocalMeta);
    }
    if (data.containsKey('sync_status')) {
      context.handle(
        _syncStatusMeta,
        syncStatus.isAcceptableOrUnknown(data['sync_status']!, _syncStatusMeta),
      );
    }
    if (data.containsKey('error_message')) {
      context.handle(
        _errorMessageMeta,
        errorMessage.isAcceptableOrUnknown(
          data['error_message']!,
          _errorMessageMeta,
        ),
      );
    }
    if (data.containsKey('remote_id')) {
      context.handle(
        _remoteIdMeta,
        remoteId.isAcceptableOrUnknown(data['remote_id']!, _remoteIdMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {clientId};
  @override
  PendingAccessLog map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PendingAccessLog(
      clientId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}client_id'],
      )!,
      propertyId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}property_id'],
      ),
      tipo: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}tipo'],
      )!,
      placas: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}placas'],
      )!,
      createdAtLocal: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at_local'],
      )!,
      syncStatus: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sync_status'],
      )!,
      errorMessage: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}error_message'],
      ),
      remoteId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}remote_id'],
      ),
    );
  }

  @override
  $PendingAccessLogsTable createAlias(String alias) {
    return $PendingAccessLogsTable(attachedDatabase, alias);
  }
}

class PendingAccessLog extends DataClass
    implements Insertable<PendingAccessLog> {
  final String clientId;
  final String? propertyId;
  final String tipo;
  final String placas;
  final DateTime createdAtLocal;
  final String syncStatus;
  final String? errorMessage;
  final String? remoteId;
  const PendingAccessLog({
    required this.clientId,
    this.propertyId,
    required this.tipo,
    required this.placas,
    required this.createdAtLocal,
    required this.syncStatus,
    this.errorMessage,
    this.remoteId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['client_id'] = Variable<String>(clientId);
    if (!nullToAbsent || propertyId != null) {
      map['property_id'] = Variable<String>(propertyId);
    }
    map['tipo'] = Variable<String>(tipo);
    map['placas'] = Variable<String>(placas);
    map['created_at_local'] = Variable<DateTime>(createdAtLocal);
    map['sync_status'] = Variable<String>(syncStatus);
    if (!nullToAbsent || errorMessage != null) {
      map['error_message'] = Variable<String>(errorMessage);
    }
    if (!nullToAbsent || remoteId != null) {
      map['remote_id'] = Variable<String>(remoteId);
    }
    return map;
  }

  PendingAccessLogsCompanion toCompanion(bool nullToAbsent) {
    return PendingAccessLogsCompanion(
      clientId: Value(clientId),
      propertyId: propertyId == null && nullToAbsent
          ? const Value.absent()
          : Value(propertyId),
      tipo: Value(tipo),
      placas: Value(placas),
      createdAtLocal: Value(createdAtLocal),
      syncStatus: Value(syncStatus),
      errorMessage: errorMessage == null && nullToAbsent
          ? const Value.absent()
          : Value(errorMessage),
      remoteId: remoteId == null && nullToAbsent
          ? const Value.absent()
          : Value(remoteId),
    );
  }

  factory PendingAccessLog.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PendingAccessLog(
      clientId: serializer.fromJson<String>(json['clientId']),
      propertyId: serializer.fromJson<String?>(json['propertyId']),
      tipo: serializer.fromJson<String>(json['tipo']),
      placas: serializer.fromJson<String>(json['placas']),
      createdAtLocal: serializer.fromJson<DateTime>(json['createdAtLocal']),
      syncStatus: serializer.fromJson<String>(json['syncStatus']),
      errorMessage: serializer.fromJson<String?>(json['errorMessage']),
      remoteId: serializer.fromJson<String?>(json['remoteId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'clientId': serializer.toJson<String>(clientId),
      'propertyId': serializer.toJson<String?>(propertyId),
      'tipo': serializer.toJson<String>(tipo),
      'placas': serializer.toJson<String>(placas),
      'createdAtLocal': serializer.toJson<DateTime>(createdAtLocal),
      'syncStatus': serializer.toJson<String>(syncStatus),
      'errorMessage': serializer.toJson<String?>(errorMessage),
      'remoteId': serializer.toJson<String?>(remoteId),
    };
  }

  PendingAccessLog copyWith({
    String? clientId,
    Value<String?> propertyId = const Value.absent(),
    String? tipo,
    String? placas,
    DateTime? createdAtLocal,
    String? syncStatus,
    Value<String?> errorMessage = const Value.absent(),
    Value<String?> remoteId = const Value.absent(),
  }) => PendingAccessLog(
    clientId: clientId ?? this.clientId,
    propertyId: propertyId.present ? propertyId.value : this.propertyId,
    tipo: tipo ?? this.tipo,
    placas: placas ?? this.placas,
    createdAtLocal: createdAtLocal ?? this.createdAtLocal,
    syncStatus: syncStatus ?? this.syncStatus,
    errorMessage: errorMessage.present ? errorMessage.value : this.errorMessage,
    remoteId: remoteId.present ? remoteId.value : this.remoteId,
  );
  PendingAccessLog copyWithCompanion(PendingAccessLogsCompanion data) {
    return PendingAccessLog(
      clientId: data.clientId.present ? data.clientId.value : this.clientId,
      propertyId: data.propertyId.present
          ? data.propertyId.value
          : this.propertyId,
      tipo: data.tipo.present ? data.tipo.value : this.tipo,
      placas: data.placas.present ? data.placas.value : this.placas,
      createdAtLocal: data.createdAtLocal.present
          ? data.createdAtLocal.value
          : this.createdAtLocal,
      syncStatus: data.syncStatus.present
          ? data.syncStatus.value
          : this.syncStatus,
      errorMessage: data.errorMessage.present
          ? data.errorMessage.value
          : this.errorMessage,
      remoteId: data.remoteId.present ? data.remoteId.value : this.remoteId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PendingAccessLog(')
          ..write('clientId: $clientId, ')
          ..write('propertyId: $propertyId, ')
          ..write('tipo: $tipo, ')
          ..write('placas: $placas, ')
          ..write('createdAtLocal: $createdAtLocal, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('remoteId: $remoteId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    clientId,
    propertyId,
    tipo,
    placas,
    createdAtLocal,
    syncStatus,
    errorMessage,
    remoteId,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PendingAccessLog &&
          other.clientId == this.clientId &&
          other.propertyId == this.propertyId &&
          other.tipo == this.tipo &&
          other.placas == this.placas &&
          other.createdAtLocal == this.createdAtLocal &&
          other.syncStatus == this.syncStatus &&
          other.errorMessage == this.errorMessage &&
          other.remoteId == this.remoteId);
}

class PendingAccessLogsCompanion extends UpdateCompanion<PendingAccessLog> {
  final Value<String> clientId;
  final Value<String?> propertyId;
  final Value<String> tipo;
  final Value<String> placas;
  final Value<DateTime> createdAtLocal;
  final Value<String> syncStatus;
  final Value<String?> errorMessage;
  final Value<String?> remoteId;
  final Value<int> rowid;
  const PendingAccessLogsCompanion({
    this.clientId = const Value.absent(),
    this.propertyId = const Value.absent(),
    this.tipo = const Value.absent(),
    this.placas = const Value.absent(),
    this.createdAtLocal = const Value.absent(),
    this.syncStatus = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.remoteId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  PendingAccessLogsCompanion.insert({
    required String clientId,
    this.propertyId = const Value.absent(),
    required String tipo,
    this.placas = const Value.absent(),
    required DateTime createdAtLocal,
    this.syncStatus = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.remoteId = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : clientId = Value(clientId),
       tipo = Value(tipo),
       createdAtLocal = Value(createdAtLocal);
  static Insertable<PendingAccessLog> custom({
    Expression<String>? clientId,
    Expression<String>? propertyId,
    Expression<String>? tipo,
    Expression<String>? placas,
    Expression<DateTime>? createdAtLocal,
    Expression<String>? syncStatus,
    Expression<String>? errorMessage,
    Expression<String>? remoteId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (clientId != null) 'client_id': clientId,
      if (propertyId != null) 'property_id': propertyId,
      if (tipo != null) 'tipo': tipo,
      if (placas != null) 'placas': placas,
      if (createdAtLocal != null) 'created_at_local': createdAtLocal,
      if (syncStatus != null) 'sync_status': syncStatus,
      if (errorMessage != null) 'error_message': errorMessage,
      if (remoteId != null) 'remote_id': remoteId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  PendingAccessLogsCompanion copyWith({
    Value<String>? clientId,
    Value<String?>? propertyId,
    Value<String>? tipo,
    Value<String>? placas,
    Value<DateTime>? createdAtLocal,
    Value<String>? syncStatus,
    Value<String?>? errorMessage,
    Value<String?>? remoteId,
    Value<int>? rowid,
  }) {
    return PendingAccessLogsCompanion(
      clientId: clientId ?? this.clientId,
      propertyId: propertyId ?? this.propertyId,
      tipo: tipo ?? this.tipo,
      placas: placas ?? this.placas,
      createdAtLocal: createdAtLocal ?? this.createdAtLocal,
      syncStatus: syncStatus ?? this.syncStatus,
      errorMessage: errorMessage ?? this.errorMessage,
      remoteId: remoteId ?? this.remoteId,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (clientId.present) {
      map['client_id'] = Variable<String>(clientId.value);
    }
    if (propertyId.present) {
      map['property_id'] = Variable<String>(propertyId.value);
    }
    if (tipo.present) {
      map['tipo'] = Variable<String>(tipo.value);
    }
    if (placas.present) {
      map['placas'] = Variable<String>(placas.value);
    }
    if (createdAtLocal.present) {
      map['created_at_local'] = Variable<DateTime>(createdAtLocal.value);
    }
    if (syncStatus.present) {
      map['sync_status'] = Variable<String>(syncStatus.value);
    }
    if (errorMessage.present) {
      map['error_message'] = Variable<String>(errorMessage.value);
    }
    if (remoteId.present) {
      map['remote_id'] = Variable<String>(remoteId.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PendingAccessLogsCompanion(')
          ..write('clientId: $clientId, ')
          ..write('propertyId: $propertyId, ')
          ..write('tipo: $tipo, ')
          ..write('placas: $placas, ')
          ..write('createdAtLocal: $createdAtLocal, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('remoteId: $remoteId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $PendingIncidentsTable extends PendingIncidents
    with TableInfo<$PendingIncidentsTable, PendingIncident> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PendingIncidentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _clientIdMeta = const VerificationMeta(
    'clientId',
  );
  @override
  late final GeneratedColumn<String> clientId = GeneratedColumn<String>(
    'client_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _descripcionMeta = const VerificationMeta(
    'descripcion',
  );
  @override
  late final GeneratedColumn<String> descripcion = GeneratedColumn<String>(
    'descripcion',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _fotoUrlMeta = const VerificationMeta(
    'fotoUrl',
  );
  @override
  late final GeneratedColumn<String> fotoUrl = GeneratedColumn<String>(
    'foto_url',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtLocalMeta = const VerificationMeta(
    'createdAtLocal',
  );
  @override
  late final GeneratedColumn<DateTime> createdAtLocal =
      GeneratedColumn<DateTime>(
        'created_at_local',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _syncStatusMeta = const VerificationMeta(
    'syncStatus',
  );
  @override
  late final GeneratedColumn<String> syncStatus = GeneratedColumn<String>(
    'sync_status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('pending'),
  );
  static const VerificationMeta _errorMessageMeta = const VerificationMeta(
    'errorMessage',
  );
  @override
  late final GeneratedColumn<String> errorMessage = GeneratedColumn<String>(
    'error_message',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _remoteIdMeta = const VerificationMeta(
    'remoteId',
  );
  @override
  late final GeneratedColumn<String> remoteId = GeneratedColumn<String>(
    'remote_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    clientId,
    descripcion,
    fotoUrl,
    createdAtLocal,
    syncStatus,
    errorMessage,
    remoteId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pending_incidents';
  @override
  VerificationContext validateIntegrity(
    Insertable<PendingIncident> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('client_id')) {
      context.handle(
        _clientIdMeta,
        clientId.isAcceptableOrUnknown(data['client_id']!, _clientIdMeta),
      );
    } else if (isInserting) {
      context.missing(_clientIdMeta);
    }
    if (data.containsKey('descripcion')) {
      context.handle(
        _descripcionMeta,
        descripcion.isAcceptableOrUnknown(
          data['descripcion']!,
          _descripcionMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_descripcionMeta);
    }
    if (data.containsKey('foto_url')) {
      context.handle(
        _fotoUrlMeta,
        fotoUrl.isAcceptableOrUnknown(data['foto_url']!, _fotoUrlMeta),
      );
    }
    if (data.containsKey('created_at_local')) {
      context.handle(
        _createdAtLocalMeta,
        createdAtLocal.isAcceptableOrUnknown(
          data['created_at_local']!,
          _createdAtLocalMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_createdAtLocalMeta);
    }
    if (data.containsKey('sync_status')) {
      context.handle(
        _syncStatusMeta,
        syncStatus.isAcceptableOrUnknown(data['sync_status']!, _syncStatusMeta),
      );
    }
    if (data.containsKey('error_message')) {
      context.handle(
        _errorMessageMeta,
        errorMessage.isAcceptableOrUnknown(
          data['error_message']!,
          _errorMessageMeta,
        ),
      );
    }
    if (data.containsKey('remote_id')) {
      context.handle(
        _remoteIdMeta,
        remoteId.isAcceptableOrUnknown(data['remote_id']!, _remoteIdMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {clientId};
  @override
  PendingIncident map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PendingIncident(
      clientId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}client_id'],
      )!,
      descripcion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}descripcion'],
      )!,
      fotoUrl: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}foto_url'],
      ),
      createdAtLocal: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at_local'],
      )!,
      syncStatus: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sync_status'],
      )!,
      errorMessage: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}error_message'],
      ),
      remoteId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}remote_id'],
      ),
    );
  }

  @override
  $PendingIncidentsTable createAlias(String alias) {
    return $PendingIncidentsTable(attachedDatabase, alias);
  }
}

class PendingIncident extends DataClass implements Insertable<PendingIncident> {
  final String clientId;
  final String descripcion;
  final String? fotoUrl;
  final DateTime createdAtLocal;
  final String syncStatus;
  final String? errorMessage;
  final String? remoteId;
  const PendingIncident({
    required this.clientId,
    required this.descripcion,
    this.fotoUrl,
    required this.createdAtLocal,
    required this.syncStatus,
    this.errorMessage,
    this.remoteId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['client_id'] = Variable<String>(clientId);
    map['descripcion'] = Variable<String>(descripcion);
    if (!nullToAbsent || fotoUrl != null) {
      map['foto_url'] = Variable<String>(fotoUrl);
    }
    map['created_at_local'] = Variable<DateTime>(createdAtLocal);
    map['sync_status'] = Variable<String>(syncStatus);
    if (!nullToAbsent || errorMessage != null) {
      map['error_message'] = Variable<String>(errorMessage);
    }
    if (!nullToAbsent || remoteId != null) {
      map['remote_id'] = Variable<String>(remoteId);
    }
    return map;
  }

  PendingIncidentsCompanion toCompanion(bool nullToAbsent) {
    return PendingIncidentsCompanion(
      clientId: Value(clientId),
      descripcion: Value(descripcion),
      fotoUrl: fotoUrl == null && nullToAbsent
          ? const Value.absent()
          : Value(fotoUrl),
      createdAtLocal: Value(createdAtLocal),
      syncStatus: Value(syncStatus),
      errorMessage: errorMessage == null && nullToAbsent
          ? const Value.absent()
          : Value(errorMessage),
      remoteId: remoteId == null && nullToAbsent
          ? const Value.absent()
          : Value(remoteId),
    );
  }

  factory PendingIncident.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PendingIncident(
      clientId: serializer.fromJson<String>(json['clientId']),
      descripcion: serializer.fromJson<String>(json['descripcion']),
      fotoUrl: serializer.fromJson<String?>(json['fotoUrl']),
      createdAtLocal: serializer.fromJson<DateTime>(json['createdAtLocal']),
      syncStatus: serializer.fromJson<String>(json['syncStatus']),
      errorMessage: serializer.fromJson<String?>(json['errorMessage']),
      remoteId: serializer.fromJson<String?>(json['remoteId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'clientId': serializer.toJson<String>(clientId),
      'descripcion': serializer.toJson<String>(descripcion),
      'fotoUrl': serializer.toJson<String?>(fotoUrl),
      'createdAtLocal': serializer.toJson<DateTime>(createdAtLocal),
      'syncStatus': serializer.toJson<String>(syncStatus),
      'errorMessage': serializer.toJson<String?>(errorMessage),
      'remoteId': serializer.toJson<String?>(remoteId),
    };
  }

  PendingIncident copyWith({
    String? clientId,
    String? descripcion,
    Value<String?> fotoUrl = const Value.absent(),
    DateTime? createdAtLocal,
    String? syncStatus,
    Value<String?> errorMessage = const Value.absent(),
    Value<String?> remoteId = const Value.absent(),
  }) => PendingIncident(
    clientId: clientId ?? this.clientId,
    descripcion: descripcion ?? this.descripcion,
    fotoUrl: fotoUrl.present ? fotoUrl.value : this.fotoUrl,
    createdAtLocal: createdAtLocal ?? this.createdAtLocal,
    syncStatus: syncStatus ?? this.syncStatus,
    errorMessage: errorMessage.present ? errorMessage.value : this.errorMessage,
    remoteId: remoteId.present ? remoteId.value : this.remoteId,
  );
  PendingIncident copyWithCompanion(PendingIncidentsCompanion data) {
    return PendingIncident(
      clientId: data.clientId.present ? data.clientId.value : this.clientId,
      descripcion: data.descripcion.present
          ? data.descripcion.value
          : this.descripcion,
      fotoUrl: data.fotoUrl.present ? data.fotoUrl.value : this.fotoUrl,
      createdAtLocal: data.createdAtLocal.present
          ? data.createdAtLocal.value
          : this.createdAtLocal,
      syncStatus: data.syncStatus.present
          ? data.syncStatus.value
          : this.syncStatus,
      errorMessage: data.errorMessage.present
          ? data.errorMessage.value
          : this.errorMessage,
      remoteId: data.remoteId.present ? data.remoteId.value : this.remoteId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PendingIncident(')
          ..write('clientId: $clientId, ')
          ..write('descripcion: $descripcion, ')
          ..write('fotoUrl: $fotoUrl, ')
          ..write('createdAtLocal: $createdAtLocal, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('remoteId: $remoteId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    clientId,
    descripcion,
    fotoUrl,
    createdAtLocal,
    syncStatus,
    errorMessage,
    remoteId,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PendingIncident &&
          other.clientId == this.clientId &&
          other.descripcion == this.descripcion &&
          other.fotoUrl == this.fotoUrl &&
          other.createdAtLocal == this.createdAtLocal &&
          other.syncStatus == this.syncStatus &&
          other.errorMessage == this.errorMessage &&
          other.remoteId == this.remoteId);
}

class PendingIncidentsCompanion extends UpdateCompanion<PendingIncident> {
  final Value<String> clientId;
  final Value<String> descripcion;
  final Value<String?> fotoUrl;
  final Value<DateTime> createdAtLocal;
  final Value<String> syncStatus;
  final Value<String?> errorMessage;
  final Value<String?> remoteId;
  final Value<int> rowid;
  const PendingIncidentsCompanion({
    this.clientId = const Value.absent(),
    this.descripcion = const Value.absent(),
    this.fotoUrl = const Value.absent(),
    this.createdAtLocal = const Value.absent(),
    this.syncStatus = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.remoteId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  PendingIncidentsCompanion.insert({
    required String clientId,
    required String descripcion,
    this.fotoUrl = const Value.absent(),
    required DateTime createdAtLocal,
    this.syncStatus = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.remoteId = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : clientId = Value(clientId),
       descripcion = Value(descripcion),
       createdAtLocal = Value(createdAtLocal);
  static Insertable<PendingIncident> custom({
    Expression<String>? clientId,
    Expression<String>? descripcion,
    Expression<String>? fotoUrl,
    Expression<DateTime>? createdAtLocal,
    Expression<String>? syncStatus,
    Expression<String>? errorMessage,
    Expression<String>? remoteId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (clientId != null) 'client_id': clientId,
      if (descripcion != null) 'descripcion': descripcion,
      if (fotoUrl != null) 'foto_url': fotoUrl,
      if (createdAtLocal != null) 'created_at_local': createdAtLocal,
      if (syncStatus != null) 'sync_status': syncStatus,
      if (errorMessage != null) 'error_message': errorMessage,
      if (remoteId != null) 'remote_id': remoteId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  PendingIncidentsCompanion copyWith({
    Value<String>? clientId,
    Value<String>? descripcion,
    Value<String?>? fotoUrl,
    Value<DateTime>? createdAtLocal,
    Value<String>? syncStatus,
    Value<String?>? errorMessage,
    Value<String?>? remoteId,
    Value<int>? rowid,
  }) {
    return PendingIncidentsCompanion(
      clientId: clientId ?? this.clientId,
      descripcion: descripcion ?? this.descripcion,
      fotoUrl: fotoUrl ?? this.fotoUrl,
      createdAtLocal: createdAtLocal ?? this.createdAtLocal,
      syncStatus: syncStatus ?? this.syncStatus,
      errorMessage: errorMessage ?? this.errorMessage,
      remoteId: remoteId ?? this.remoteId,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (clientId.present) {
      map['client_id'] = Variable<String>(clientId.value);
    }
    if (descripcion.present) {
      map['descripcion'] = Variable<String>(descripcion.value);
    }
    if (fotoUrl.present) {
      map['foto_url'] = Variable<String>(fotoUrl.value);
    }
    if (createdAtLocal.present) {
      map['created_at_local'] = Variable<DateTime>(createdAtLocal.value);
    }
    if (syncStatus.present) {
      map['sync_status'] = Variable<String>(syncStatus.value);
    }
    if (errorMessage.present) {
      map['error_message'] = Variable<String>(errorMessage.value);
    }
    if (remoteId.present) {
      map['remote_id'] = Variable<String>(remoteId.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PendingIncidentsCompanion(')
          ..write('clientId: $clientId, ')
          ..write('descripcion: $descripcion, ')
          ..write('fotoUrl: $fotoUrl, ')
          ..write('createdAtLocal: $createdAtLocal, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('remoteId: $remoteId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $PendingAccessLogsTable pendingAccessLogs =
      $PendingAccessLogsTable(this);
  late final $PendingIncidentsTable pendingIncidents = $PendingIncidentsTable(
    this,
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    pendingAccessLogs,
    pendingIncidents,
  ];
}

typedef $$PendingAccessLogsTableCreateCompanionBuilder =
    PendingAccessLogsCompanion Function({
      required String clientId,
      Value<String?> propertyId,
      required String tipo,
      Value<String> placas,
      required DateTime createdAtLocal,
      Value<String> syncStatus,
      Value<String?> errorMessage,
      Value<String?> remoteId,
      Value<int> rowid,
    });
typedef $$PendingAccessLogsTableUpdateCompanionBuilder =
    PendingAccessLogsCompanion Function({
      Value<String> clientId,
      Value<String?> propertyId,
      Value<String> tipo,
      Value<String> placas,
      Value<DateTime> createdAtLocal,
      Value<String> syncStatus,
      Value<String?> errorMessage,
      Value<String?> remoteId,
      Value<int> rowid,
    });

class $$PendingAccessLogsTableFilterComposer
    extends Composer<_$AppDatabase, $PendingAccessLogsTable> {
  $$PendingAccessLogsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get clientId => $composableBuilder(
    column: $table.clientId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get propertyId => $composableBuilder(
    column: $table.propertyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get tipo => $composableBuilder(
    column: $table.tipo,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get placas => $composableBuilder(
    column: $table.placas,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAtLocal => $composableBuilder(
    column: $table.createdAtLocal,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get remoteId => $composableBuilder(
    column: $table.remoteId,
    builder: (column) => ColumnFilters(column),
  );
}

class $$PendingAccessLogsTableOrderingComposer
    extends Composer<_$AppDatabase, $PendingAccessLogsTable> {
  $$PendingAccessLogsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get clientId => $composableBuilder(
    column: $table.clientId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get propertyId => $composableBuilder(
    column: $table.propertyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get tipo => $composableBuilder(
    column: $table.tipo,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get placas => $composableBuilder(
    column: $table.placas,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAtLocal => $composableBuilder(
    column: $table.createdAtLocal,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get remoteId => $composableBuilder(
    column: $table.remoteId,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$PendingAccessLogsTableAnnotationComposer
    extends Composer<_$AppDatabase, $PendingAccessLogsTable> {
  $$PendingAccessLogsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get clientId =>
      $composableBuilder(column: $table.clientId, builder: (column) => column);

  GeneratedColumn<String> get propertyId => $composableBuilder(
    column: $table.propertyId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get tipo =>
      $composableBuilder(column: $table.tipo, builder: (column) => column);

  GeneratedColumn<String> get placas =>
      $composableBuilder(column: $table.placas, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAtLocal => $composableBuilder(
    column: $table.createdAtLocal,
    builder: (column) => column,
  );

  GeneratedColumn<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => column,
  );

  GeneratedColumn<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => column,
  );

  GeneratedColumn<String> get remoteId =>
      $composableBuilder(column: $table.remoteId, builder: (column) => column);
}

class $$PendingAccessLogsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PendingAccessLogsTable,
          PendingAccessLog,
          $$PendingAccessLogsTableFilterComposer,
          $$PendingAccessLogsTableOrderingComposer,
          $$PendingAccessLogsTableAnnotationComposer,
          $$PendingAccessLogsTableCreateCompanionBuilder,
          $$PendingAccessLogsTableUpdateCompanionBuilder,
          (
            PendingAccessLog,
            BaseReferences<
              _$AppDatabase,
              $PendingAccessLogsTable,
              PendingAccessLog
            >,
          ),
          PendingAccessLog,
          PrefetchHooks Function()
        > {
  $$PendingAccessLogsTableTableManager(
    _$AppDatabase db,
    $PendingAccessLogsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PendingAccessLogsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PendingAccessLogsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PendingAccessLogsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> clientId = const Value.absent(),
                Value<String?> propertyId = const Value.absent(),
                Value<String> tipo = const Value.absent(),
                Value<String> placas = const Value.absent(),
                Value<DateTime> createdAtLocal = const Value.absent(),
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingAccessLogsCompanion(
                clientId: clientId,
                propertyId: propertyId,
                tipo: tipo,
                placas: placas,
                createdAtLocal: createdAtLocal,
                syncStatus: syncStatus,
                errorMessage: errorMessage,
                remoteId: remoteId,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String clientId,
                Value<String?> propertyId = const Value.absent(),
                required String tipo,
                Value<String> placas = const Value.absent(),
                required DateTime createdAtLocal,
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingAccessLogsCompanion.insert(
                clientId: clientId,
                propertyId: propertyId,
                tipo: tipo,
                placas: placas,
                createdAtLocal: createdAtLocal,
                syncStatus: syncStatus,
                errorMessage: errorMessage,
                remoteId: remoteId,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$PendingAccessLogsTable, PendingAccessLog>(table),
                  BaseReferences<
                    _$AppDatabase,
                    $PendingAccessLogsTable,
                    PendingAccessLog
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PendingAccessLogsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PendingAccessLogsTable,
      PendingAccessLog,
      $$PendingAccessLogsTableFilterComposer,
      $$PendingAccessLogsTableOrderingComposer,
      $$PendingAccessLogsTableAnnotationComposer,
      $$PendingAccessLogsTableCreateCompanionBuilder,
      $$PendingAccessLogsTableUpdateCompanionBuilder,
      (
        PendingAccessLog,
        BaseReferences<
          _$AppDatabase,
          $PendingAccessLogsTable,
          PendingAccessLog
        >,
      ),
      PendingAccessLog,
      PrefetchHooks Function()
    >;
typedef $$PendingIncidentsTableCreateCompanionBuilder =
    PendingIncidentsCompanion Function({
      required String clientId,
      required String descripcion,
      Value<String?> fotoUrl,
      required DateTime createdAtLocal,
      Value<String> syncStatus,
      Value<String?> errorMessage,
      Value<String?> remoteId,
      Value<int> rowid,
    });
typedef $$PendingIncidentsTableUpdateCompanionBuilder =
    PendingIncidentsCompanion Function({
      Value<String> clientId,
      Value<String> descripcion,
      Value<String?> fotoUrl,
      Value<DateTime> createdAtLocal,
      Value<String> syncStatus,
      Value<String?> errorMessage,
      Value<String?> remoteId,
      Value<int> rowid,
    });

class $$PendingIncidentsTableFilterComposer
    extends Composer<_$AppDatabase, $PendingIncidentsTable> {
  $$PendingIncidentsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get clientId => $composableBuilder(
    column: $table.clientId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get descripcion => $composableBuilder(
    column: $table.descripcion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fotoUrl => $composableBuilder(
    column: $table.fotoUrl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAtLocal => $composableBuilder(
    column: $table.createdAtLocal,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get remoteId => $composableBuilder(
    column: $table.remoteId,
    builder: (column) => ColumnFilters(column),
  );
}

class $$PendingIncidentsTableOrderingComposer
    extends Composer<_$AppDatabase, $PendingIncidentsTable> {
  $$PendingIncidentsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get clientId => $composableBuilder(
    column: $table.clientId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get descripcion => $composableBuilder(
    column: $table.descripcion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fotoUrl => $composableBuilder(
    column: $table.fotoUrl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAtLocal => $composableBuilder(
    column: $table.createdAtLocal,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get remoteId => $composableBuilder(
    column: $table.remoteId,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$PendingIncidentsTableAnnotationComposer
    extends Composer<_$AppDatabase, $PendingIncidentsTable> {
  $$PendingIncidentsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get clientId =>
      $composableBuilder(column: $table.clientId, builder: (column) => column);

  GeneratedColumn<String> get descripcion => $composableBuilder(
    column: $table.descripcion,
    builder: (column) => column,
  );

  GeneratedColumn<String> get fotoUrl =>
      $composableBuilder(column: $table.fotoUrl, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAtLocal => $composableBuilder(
    column: $table.createdAtLocal,
    builder: (column) => column,
  );

  GeneratedColumn<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => column,
  );

  GeneratedColumn<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => column,
  );

  GeneratedColumn<String> get remoteId =>
      $composableBuilder(column: $table.remoteId, builder: (column) => column);
}

class $$PendingIncidentsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PendingIncidentsTable,
          PendingIncident,
          $$PendingIncidentsTableFilterComposer,
          $$PendingIncidentsTableOrderingComposer,
          $$PendingIncidentsTableAnnotationComposer,
          $$PendingIncidentsTableCreateCompanionBuilder,
          $$PendingIncidentsTableUpdateCompanionBuilder,
          (
            PendingIncident,
            BaseReferences<
              _$AppDatabase,
              $PendingIncidentsTable,
              PendingIncident
            >,
          ),
          PendingIncident,
          PrefetchHooks Function()
        > {
  $$PendingIncidentsTableTableManager(
    _$AppDatabase db,
    $PendingIncidentsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PendingIncidentsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PendingIncidentsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PendingIncidentsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> clientId = const Value.absent(),
                Value<String> descripcion = const Value.absent(),
                Value<String?> fotoUrl = const Value.absent(),
                Value<DateTime> createdAtLocal = const Value.absent(),
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingIncidentsCompanion(
                clientId: clientId,
                descripcion: descripcion,
                fotoUrl: fotoUrl,
                createdAtLocal: createdAtLocal,
                syncStatus: syncStatus,
                errorMessage: errorMessage,
                remoteId: remoteId,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String clientId,
                required String descripcion,
                Value<String?> fotoUrl = const Value.absent(),
                required DateTime createdAtLocal,
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingIncidentsCompanion.insert(
                clientId: clientId,
                descripcion: descripcion,
                fotoUrl: fotoUrl,
                createdAtLocal: createdAtLocal,
                syncStatus: syncStatus,
                errorMessage: errorMessage,
                remoteId: remoteId,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$PendingIncidentsTable, PendingIncident>(table),
                  BaseReferences<
                    _$AppDatabase,
                    $PendingIncidentsTable,
                    PendingIncident
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PendingIncidentsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PendingIncidentsTable,
      PendingIncident,
      $$PendingIncidentsTableFilterComposer,
      $$PendingIncidentsTableOrderingComposer,
      $$PendingIncidentsTableAnnotationComposer,
      $$PendingIncidentsTableCreateCompanionBuilder,
      $$PendingIncidentsTableUpdateCompanionBuilder,
      (
        PendingIncident,
        BaseReferences<_$AppDatabase, $PendingIncidentsTable, PendingIncident>,
      ),
      PendingIncident,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$PendingAccessLogsTableTableManager get pendingAccessLogs =>
      $$PendingAccessLogsTableTableManager(_db, _db.pendingAccessLogs);
  $$PendingIncidentsTableTableManager get pendingIncidents =>
      $$PendingIncidentsTableTableManager(_db, _db.pendingIncidents);
}
