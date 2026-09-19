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
  static const VerificationMeta _nombreVisitanteMeta = const VerificationMeta(
    'nombreVisitante',
  );
  @override
  late final GeneratedColumn<String> nombreVisitante = GeneratedColumn<String>(
    'nombre_visitante',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _acompanantesMeta = const VerificationMeta(
    'acompanantes',
  );
  @override
  late final GeneratedColumn<int> acompanantes = GeneratedColumn<int>(
    'acompanantes',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _identificacionMeta = const VerificationMeta(
    'identificacion',
  );
  @override
  late final GeneratedColumn<String> identificacion = GeneratedColumn<String>(
    'identificacion',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _autorizadoPorMeta = const VerificationMeta(
    'autorizadoPor',
  );
  @override
  late final GeneratedColumn<String> autorizadoPor = GeneratedColumn<String>(
    'autorizado_por',
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
    propertyId,
    tipo,
    placas,
    nombreVisitante,
    acompanantes,
    identificacion,
    autorizadoPor,
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
    if (data.containsKey('nombre_visitante')) {
      context.handle(
        _nombreVisitanteMeta,
        nombreVisitante.isAcceptableOrUnknown(
          data['nombre_visitante']!,
          _nombreVisitanteMeta,
        ),
      );
    }
    if (data.containsKey('acompanantes')) {
      context.handle(
        _acompanantesMeta,
        acompanantes.isAcceptableOrUnknown(
          data['acompanantes']!,
          _acompanantesMeta,
        ),
      );
    }
    if (data.containsKey('identificacion')) {
      context.handle(
        _identificacionMeta,
        identificacion.isAcceptableOrUnknown(
          data['identificacion']!,
          _identificacionMeta,
        ),
      );
    }
    if (data.containsKey('autorizado_por')) {
      context.handle(
        _autorizadoPorMeta,
        autorizadoPor.isAcceptableOrUnknown(
          data['autorizado_por']!,
          _autorizadoPorMeta,
        ),
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
      nombreVisitante: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}nombre_visitante'],
      ),
      acompanantes: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}acompanantes'],
      )!,
      identificacion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}identificacion'],
      ),
      autorizadoPor: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}autorizado_por'],
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
  final String? nombreVisitante;
  final int acompanantes;
  final String? identificacion;
  final String? autorizadoPor;
  final DateTime createdAtLocal;
  final String syncStatus;
  final String? errorMessage;
  final String? remoteId;
  const PendingAccessLog({
    required this.clientId,
    this.propertyId,
    required this.tipo,
    required this.placas,
    this.nombreVisitante,
    required this.acompanantes,
    this.identificacion,
    this.autorizadoPor,
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
    if (!nullToAbsent || nombreVisitante != null) {
      map['nombre_visitante'] = Variable<String>(nombreVisitante);
    }
    map['acompanantes'] = Variable<int>(acompanantes);
    if (!nullToAbsent || identificacion != null) {
      map['identificacion'] = Variable<String>(identificacion);
    }
    if (!nullToAbsent || autorizadoPor != null) {
      map['autorizado_por'] = Variable<String>(autorizadoPor);
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

  PendingAccessLogsCompanion toCompanion(bool nullToAbsent) {
    return PendingAccessLogsCompanion(
      clientId: Value(clientId),
      propertyId: propertyId == null && nullToAbsent
          ? const Value.absent()
          : Value(propertyId),
      tipo: Value(tipo),
      placas: Value(placas),
      nombreVisitante: nombreVisitante == null && nullToAbsent
          ? const Value.absent()
          : Value(nombreVisitante),
      acompanantes: Value(acompanantes),
      identificacion: identificacion == null && nullToAbsent
          ? const Value.absent()
          : Value(identificacion),
      autorizadoPor: autorizadoPor == null && nullToAbsent
          ? const Value.absent()
          : Value(autorizadoPor),
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
      nombreVisitante: serializer.fromJson<String?>(json['nombreVisitante']),
      acompanantes: serializer.fromJson<int>(json['acompanantes']),
      identificacion: serializer.fromJson<String?>(json['identificacion']),
      autorizadoPor: serializer.fromJson<String?>(json['autorizadoPor']),
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
      'nombreVisitante': serializer.toJson<String?>(nombreVisitante),
      'acompanantes': serializer.toJson<int>(acompanantes),
      'identificacion': serializer.toJson<String?>(identificacion),
      'autorizadoPor': serializer.toJson<String?>(autorizadoPor),
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
    Value<String?> nombreVisitante = const Value.absent(),
    int? acompanantes,
    Value<String?> identificacion = const Value.absent(),
    Value<String?> autorizadoPor = const Value.absent(),
    DateTime? createdAtLocal,
    String? syncStatus,
    Value<String?> errorMessage = const Value.absent(),
    Value<String?> remoteId = const Value.absent(),
  }) => PendingAccessLog(
    clientId: clientId ?? this.clientId,
    propertyId: propertyId.present ? propertyId.value : this.propertyId,
    tipo: tipo ?? this.tipo,
    placas: placas ?? this.placas,
    nombreVisitante: nombreVisitante.present
        ? nombreVisitante.value
        : this.nombreVisitante,
    acompanantes: acompanantes ?? this.acompanantes,
    identificacion: identificacion.present
        ? identificacion.value
        : this.identificacion,
    autorizadoPor: autorizadoPor.present
        ? autorizadoPor.value
        : this.autorizadoPor,
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
      nombreVisitante: data.nombreVisitante.present
          ? data.nombreVisitante.value
          : this.nombreVisitante,
      acompanantes: data.acompanantes.present
          ? data.acompanantes.value
          : this.acompanantes,
      identificacion: data.identificacion.present
          ? data.identificacion.value
          : this.identificacion,
      autorizadoPor: data.autorizadoPor.present
          ? data.autorizadoPor.value
          : this.autorizadoPor,
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
          ..write('nombreVisitante: $nombreVisitante, ')
          ..write('acompanantes: $acompanantes, ')
          ..write('identificacion: $identificacion, ')
          ..write('autorizadoPor: $autorizadoPor, ')
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
    nombreVisitante,
    acompanantes,
    identificacion,
    autorizadoPor,
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
          other.nombreVisitante == this.nombreVisitante &&
          other.acompanantes == this.acompanantes &&
          other.identificacion == this.identificacion &&
          other.autorizadoPor == this.autorizadoPor &&
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
  final Value<String?> nombreVisitante;
  final Value<int> acompanantes;
  final Value<String?> identificacion;
  final Value<String?> autorizadoPor;
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
    this.nombreVisitante = const Value.absent(),
    this.acompanantes = const Value.absent(),
    this.identificacion = const Value.absent(),
    this.autorizadoPor = const Value.absent(),
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
    this.nombreVisitante = const Value.absent(),
    this.acompanantes = const Value.absent(),
    this.identificacion = const Value.absent(),
    this.autorizadoPor = const Value.absent(),
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
    Expression<String>? nombreVisitante,
    Expression<int>? acompanantes,
    Expression<String>? identificacion,
    Expression<String>? autorizadoPor,
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
      if (nombreVisitante != null) 'nombre_visitante': nombreVisitante,
      if (acompanantes != null) 'acompanantes': acompanantes,
      if (identificacion != null) 'identificacion': identificacion,
      if (autorizadoPor != null) 'autorizado_por': autorizadoPor,
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
    Value<String?>? nombreVisitante,
    Value<int>? acompanantes,
    Value<String?>? identificacion,
    Value<String?>? autorizadoPor,
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
      nombreVisitante: nombreVisitante ?? this.nombreVisitante,
      acompanantes: acompanantes ?? this.acompanantes,
      identificacion: identificacion ?? this.identificacion,
      autorizadoPor: autorizadoPor ?? this.autorizadoPor,
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
    if (nombreVisitante.present) {
      map['nombre_visitante'] = Variable<String>(nombreVisitante.value);
    }
    if (acompanantes.present) {
      map['acompanantes'] = Variable<int>(acompanantes.value);
    }
    if (identificacion.present) {
      map['identificacion'] = Variable<String>(identificacion.value);
    }
    if (autorizadoPor.present) {
      map['autorizado_por'] = Variable<String>(autorizadoPor.value);
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
          ..write('nombreVisitante: $nombreVisitante, ')
          ..write('acompanantes: $acompanantes, ')
          ..write('identificacion: $identificacion, ')
          ..write('autorizadoPor: $autorizadoPor, ')
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
  static const VerificationMeta _tipoMeta = const VerificationMeta('tipo');
  @override
  late final GeneratedColumn<String> tipo = GeneratedColumn<String>(
    'tipo',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('seguridad'),
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
  static const VerificationMeta _personaInvolucradaMeta =
      const VerificationMeta('personaInvolucrada');
  @override
  late final GeneratedColumn<String> personaInvolucrada =
      GeneratedColumn<String>(
        'persona_involucrada',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _fotoBytesMeta = const VerificationMeta(
    'fotoBytes',
  );
  @override
  late final GeneratedColumn<Uint8List> fotoBytes = GeneratedColumn<Uint8List>(
    'foto_bytes',
    aliasedName,
    true,
    type: DriftSqlType.blob,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _fotoNombreMeta = const VerificationMeta(
    'fotoNombre',
  );
  @override
  late final GeneratedColumn<String> fotoNombre = GeneratedColumn<String>(
    'foto_nombre',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _fotoArchivoIdMeta = const VerificationMeta(
    'fotoArchivoId',
  );
  @override
  late final GeneratedColumn<String> fotoArchivoId = GeneratedColumn<String>(
    'foto_archivo_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _fotoDescartadaMeta = const VerificationMeta(
    'fotoDescartada',
  );
  @override
  late final GeneratedColumn<bool> fotoDescartada = GeneratedColumn<bool>(
    'foto_descartada',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("foto_descartada" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
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
    tipo,
    propertyId,
    personaInvolucrada,
    fotoBytes,
    fotoNombre,
    fotoArchivoId,
    fotoDescartada,
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
    if (data.containsKey('tipo')) {
      context.handle(
        _tipoMeta,
        tipo.isAcceptableOrUnknown(data['tipo']!, _tipoMeta),
      );
    }
    if (data.containsKey('property_id')) {
      context.handle(
        _propertyIdMeta,
        propertyId.isAcceptableOrUnknown(data['property_id']!, _propertyIdMeta),
      );
    }
    if (data.containsKey('persona_involucrada')) {
      context.handle(
        _personaInvolucradaMeta,
        personaInvolucrada.isAcceptableOrUnknown(
          data['persona_involucrada']!,
          _personaInvolucradaMeta,
        ),
      );
    }
    if (data.containsKey('foto_bytes')) {
      context.handle(
        _fotoBytesMeta,
        fotoBytes.isAcceptableOrUnknown(data['foto_bytes']!, _fotoBytesMeta),
      );
    }
    if (data.containsKey('foto_nombre')) {
      context.handle(
        _fotoNombreMeta,
        fotoNombre.isAcceptableOrUnknown(data['foto_nombre']!, _fotoNombreMeta),
      );
    }
    if (data.containsKey('foto_archivo_id')) {
      context.handle(
        _fotoArchivoIdMeta,
        fotoArchivoId.isAcceptableOrUnknown(
          data['foto_archivo_id']!,
          _fotoArchivoIdMeta,
        ),
      );
    }
    if (data.containsKey('foto_descartada')) {
      context.handle(
        _fotoDescartadaMeta,
        fotoDescartada.isAcceptableOrUnknown(
          data['foto_descartada']!,
          _fotoDescartadaMeta,
        ),
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
      tipo: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}tipo'],
      )!,
      propertyId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}property_id'],
      ),
      personaInvolucrada: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}persona_involucrada'],
      ),
      fotoBytes: attachedDatabase.typeMapping.read(
        DriftSqlType.blob,
        data['${effectivePrefix}foto_bytes'],
      ),
      fotoNombre: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}foto_nombre'],
      ),
      fotoArchivoId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}foto_archivo_id'],
      ),
      fotoDescartada: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}foto_descartada'],
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
  $PendingIncidentsTable createAlias(String alias) {
    return $PendingIncidentsTable(attachedDatabase, alias);
  }
}

class PendingIncident extends DataClass implements Insertable<PendingIncident> {
  final String clientId;
  final String descripcion;
  final String? fotoUrl;
  final String tipo;
  final String? propertyId;
  final String? personaInvolucrada;
  final Uint8List? fotoBytes;
  final String? fotoNombre;
  final String? fotoArchivoId;
  final bool fotoDescartada;
  final DateTime createdAtLocal;
  final String syncStatus;
  final String? errorMessage;
  final String? remoteId;
  const PendingIncident({
    required this.clientId,
    required this.descripcion,
    this.fotoUrl,
    required this.tipo,
    this.propertyId,
    this.personaInvolucrada,
    this.fotoBytes,
    this.fotoNombre,
    this.fotoArchivoId,
    required this.fotoDescartada,
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
    map['tipo'] = Variable<String>(tipo);
    if (!nullToAbsent || propertyId != null) {
      map['property_id'] = Variable<String>(propertyId);
    }
    if (!nullToAbsent || personaInvolucrada != null) {
      map['persona_involucrada'] = Variable<String>(personaInvolucrada);
    }
    if (!nullToAbsent || fotoBytes != null) {
      map['foto_bytes'] = Variable<Uint8List>(fotoBytes);
    }
    if (!nullToAbsent || fotoNombre != null) {
      map['foto_nombre'] = Variable<String>(fotoNombre);
    }
    if (!nullToAbsent || fotoArchivoId != null) {
      map['foto_archivo_id'] = Variable<String>(fotoArchivoId);
    }
    map['foto_descartada'] = Variable<bool>(fotoDescartada);
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
      tipo: Value(tipo),
      propertyId: propertyId == null && nullToAbsent
          ? const Value.absent()
          : Value(propertyId),
      personaInvolucrada: personaInvolucrada == null && nullToAbsent
          ? const Value.absent()
          : Value(personaInvolucrada),
      fotoBytes: fotoBytes == null && nullToAbsent
          ? const Value.absent()
          : Value(fotoBytes),
      fotoNombre: fotoNombre == null && nullToAbsent
          ? const Value.absent()
          : Value(fotoNombre),
      fotoArchivoId: fotoArchivoId == null && nullToAbsent
          ? const Value.absent()
          : Value(fotoArchivoId),
      fotoDescartada: Value(fotoDescartada),
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
      tipo: serializer.fromJson<String>(json['tipo']),
      propertyId: serializer.fromJson<String?>(json['propertyId']),
      personaInvolucrada: serializer.fromJson<String?>(
        json['personaInvolucrada'],
      ),
      fotoBytes: serializer.fromJson<Uint8List?>(json['fotoBytes']),
      fotoNombre: serializer.fromJson<String?>(json['fotoNombre']),
      fotoArchivoId: serializer.fromJson<String?>(json['fotoArchivoId']),
      fotoDescartada: serializer.fromJson<bool>(json['fotoDescartada']),
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
      'tipo': serializer.toJson<String>(tipo),
      'propertyId': serializer.toJson<String?>(propertyId),
      'personaInvolucrada': serializer.toJson<String?>(personaInvolucrada),
      'fotoBytes': serializer.toJson<Uint8List?>(fotoBytes),
      'fotoNombre': serializer.toJson<String?>(fotoNombre),
      'fotoArchivoId': serializer.toJson<String?>(fotoArchivoId),
      'fotoDescartada': serializer.toJson<bool>(fotoDescartada),
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
    String? tipo,
    Value<String?> propertyId = const Value.absent(),
    Value<String?> personaInvolucrada = const Value.absent(),
    Value<Uint8List?> fotoBytes = const Value.absent(),
    Value<String?> fotoNombre = const Value.absent(),
    Value<String?> fotoArchivoId = const Value.absent(),
    bool? fotoDescartada,
    DateTime? createdAtLocal,
    String? syncStatus,
    Value<String?> errorMessage = const Value.absent(),
    Value<String?> remoteId = const Value.absent(),
  }) => PendingIncident(
    clientId: clientId ?? this.clientId,
    descripcion: descripcion ?? this.descripcion,
    fotoUrl: fotoUrl.present ? fotoUrl.value : this.fotoUrl,
    tipo: tipo ?? this.tipo,
    propertyId: propertyId.present ? propertyId.value : this.propertyId,
    personaInvolucrada: personaInvolucrada.present
        ? personaInvolucrada.value
        : this.personaInvolucrada,
    fotoBytes: fotoBytes.present ? fotoBytes.value : this.fotoBytes,
    fotoNombre: fotoNombre.present ? fotoNombre.value : this.fotoNombre,
    fotoArchivoId: fotoArchivoId.present
        ? fotoArchivoId.value
        : this.fotoArchivoId,
    fotoDescartada: fotoDescartada ?? this.fotoDescartada,
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
      tipo: data.tipo.present ? data.tipo.value : this.tipo,
      propertyId: data.propertyId.present
          ? data.propertyId.value
          : this.propertyId,
      personaInvolucrada: data.personaInvolucrada.present
          ? data.personaInvolucrada.value
          : this.personaInvolucrada,
      fotoBytes: data.fotoBytes.present ? data.fotoBytes.value : this.fotoBytes,
      fotoNombre: data.fotoNombre.present
          ? data.fotoNombre.value
          : this.fotoNombre,
      fotoArchivoId: data.fotoArchivoId.present
          ? data.fotoArchivoId.value
          : this.fotoArchivoId,
      fotoDescartada: data.fotoDescartada.present
          ? data.fotoDescartada.value
          : this.fotoDescartada,
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
          ..write('tipo: $tipo, ')
          ..write('propertyId: $propertyId, ')
          ..write('personaInvolucrada: $personaInvolucrada, ')
          ..write('fotoBytes: $fotoBytes, ')
          ..write('fotoNombre: $fotoNombre, ')
          ..write('fotoArchivoId: $fotoArchivoId, ')
          ..write('fotoDescartada: $fotoDescartada, ')
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
    tipo,
    propertyId,
    personaInvolucrada,
    $driftBlobEquality.hash(fotoBytes),
    fotoNombre,
    fotoArchivoId,
    fotoDescartada,
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
          other.tipo == this.tipo &&
          other.propertyId == this.propertyId &&
          other.personaInvolucrada == this.personaInvolucrada &&
          $driftBlobEquality.equals(other.fotoBytes, this.fotoBytes) &&
          other.fotoNombre == this.fotoNombre &&
          other.fotoArchivoId == this.fotoArchivoId &&
          other.fotoDescartada == this.fotoDescartada &&
          other.createdAtLocal == this.createdAtLocal &&
          other.syncStatus == this.syncStatus &&
          other.errorMessage == this.errorMessage &&
          other.remoteId == this.remoteId);
}

class PendingIncidentsCompanion extends UpdateCompanion<PendingIncident> {
  final Value<String> clientId;
  final Value<String> descripcion;
  final Value<String?> fotoUrl;
  final Value<String> tipo;
  final Value<String?> propertyId;
  final Value<String?> personaInvolucrada;
  final Value<Uint8List?> fotoBytes;
  final Value<String?> fotoNombre;
  final Value<String?> fotoArchivoId;
  final Value<bool> fotoDescartada;
  final Value<DateTime> createdAtLocal;
  final Value<String> syncStatus;
  final Value<String?> errorMessage;
  final Value<String?> remoteId;
  final Value<int> rowid;
  const PendingIncidentsCompanion({
    this.clientId = const Value.absent(),
    this.descripcion = const Value.absent(),
    this.fotoUrl = const Value.absent(),
    this.tipo = const Value.absent(),
    this.propertyId = const Value.absent(),
    this.personaInvolucrada = const Value.absent(),
    this.fotoBytes = const Value.absent(),
    this.fotoNombre = const Value.absent(),
    this.fotoArchivoId = const Value.absent(),
    this.fotoDescartada = const Value.absent(),
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
    this.tipo = const Value.absent(),
    this.propertyId = const Value.absent(),
    this.personaInvolucrada = const Value.absent(),
    this.fotoBytes = const Value.absent(),
    this.fotoNombre = const Value.absent(),
    this.fotoArchivoId = const Value.absent(),
    this.fotoDescartada = const Value.absent(),
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
    Expression<String>? tipo,
    Expression<String>? propertyId,
    Expression<String>? personaInvolucrada,
    Expression<Uint8List>? fotoBytes,
    Expression<String>? fotoNombre,
    Expression<String>? fotoArchivoId,
    Expression<bool>? fotoDescartada,
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
      if (tipo != null) 'tipo': tipo,
      if (propertyId != null) 'property_id': propertyId,
      if (personaInvolucrada != null) 'persona_involucrada': personaInvolucrada,
      if (fotoBytes != null) 'foto_bytes': fotoBytes,
      if (fotoNombre != null) 'foto_nombre': fotoNombre,
      if (fotoArchivoId != null) 'foto_archivo_id': fotoArchivoId,
      if (fotoDescartada != null) 'foto_descartada': fotoDescartada,
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
    Value<String>? tipo,
    Value<String?>? propertyId,
    Value<String?>? personaInvolucrada,
    Value<Uint8List?>? fotoBytes,
    Value<String?>? fotoNombre,
    Value<String?>? fotoArchivoId,
    Value<bool>? fotoDescartada,
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
      tipo: tipo ?? this.tipo,
      propertyId: propertyId ?? this.propertyId,
      personaInvolucrada: personaInvolucrada ?? this.personaInvolucrada,
      fotoBytes: fotoBytes ?? this.fotoBytes,
      fotoNombre: fotoNombre ?? this.fotoNombre,
      fotoArchivoId: fotoArchivoId ?? this.fotoArchivoId,
      fotoDescartada: fotoDescartada ?? this.fotoDescartada,
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
    if (tipo.present) {
      map['tipo'] = Variable<String>(tipo.value);
    }
    if (propertyId.present) {
      map['property_id'] = Variable<String>(propertyId.value);
    }
    if (personaInvolucrada.present) {
      map['persona_involucrada'] = Variable<String>(personaInvolucrada.value);
    }
    if (fotoBytes.present) {
      map['foto_bytes'] = Variable<Uint8List>(fotoBytes.value);
    }
    if (fotoNombre.present) {
      map['foto_nombre'] = Variable<String>(fotoNombre.value);
    }
    if (fotoArchivoId.present) {
      map['foto_archivo_id'] = Variable<String>(fotoArchivoId.value);
    }
    if (fotoDescartada.present) {
      map['foto_descartada'] = Variable<bool>(fotoDescartada.value);
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
          ..write('tipo: $tipo, ')
          ..write('propertyId: $propertyId, ')
          ..write('personaInvolucrada: $personaInvolucrada, ')
          ..write('fotoBytes: $fotoBytes, ')
          ..write('fotoNombre: $fotoNombre, ')
          ..write('fotoArchivoId: $fotoArchivoId, ')
          ..write('fotoDescartada: $fotoDescartada, ')
          ..write('createdAtLocal: $createdAtLocal, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('remoteId: $remoteId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $PendingPackagesTable extends PendingPackages
    with TableInfo<$PendingPackagesTable, PendingPackage> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PendingPackagesTable(this.attachedDatabase, [this._alias]);
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
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
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
    createdAtLocal,
    syncStatus,
    errorMessage,
    remoteId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pending_packages';
  @override
  VerificationContext validateIntegrity(
    Insertable<PendingPackage> instance, {
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
    } else if (isInserting) {
      context.missing(_propertyIdMeta);
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
  PendingPackage map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PendingPackage(
      clientId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}client_id'],
      )!,
      propertyId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}property_id'],
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
  $PendingPackagesTable createAlias(String alias) {
    return $PendingPackagesTable(attachedDatabase, alias);
  }
}

class PendingPackage extends DataClass implements Insertable<PendingPackage> {
  final String clientId;
  final String propertyId;
  final DateTime createdAtLocal;
  final String syncStatus;
  final String? errorMessage;
  final String? remoteId;
  const PendingPackage({
    required this.clientId,
    required this.propertyId,
    required this.createdAtLocal,
    required this.syncStatus,
    this.errorMessage,
    this.remoteId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['client_id'] = Variable<String>(clientId);
    map['property_id'] = Variable<String>(propertyId);
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

  PendingPackagesCompanion toCompanion(bool nullToAbsent) {
    return PendingPackagesCompanion(
      clientId: Value(clientId),
      propertyId: Value(propertyId),
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

  factory PendingPackage.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PendingPackage(
      clientId: serializer.fromJson<String>(json['clientId']),
      propertyId: serializer.fromJson<String>(json['propertyId']),
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
      'propertyId': serializer.toJson<String>(propertyId),
      'createdAtLocal': serializer.toJson<DateTime>(createdAtLocal),
      'syncStatus': serializer.toJson<String>(syncStatus),
      'errorMessage': serializer.toJson<String?>(errorMessage),
      'remoteId': serializer.toJson<String?>(remoteId),
    };
  }

  PendingPackage copyWith({
    String? clientId,
    String? propertyId,
    DateTime? createdAtLocal,
    String? syncStatus,
    Value<String?> errorMessage = const Value.absent(),
    Value<String?> remoteId = const Value.absent(),
  }) => PendingPackage(
    clientId: clientId ?? this.clientId,
    propertyId: propertyId ?? this.propertyId,
    createdAtLocal: createdAtLocal ?? this.createdAtLocal,
    syncStatus: syncStatus ?? this.syncStatus,
    errorMessage: errorMessage.present ? errorMessage.value : this.errorMessage,
    remoteId: remoteId.present ? remoteId.value : this.remoteId,
  );
  PendingPackage copyWithCompanion(PendingPackagesCompanion data) {
    return PendingPackage(
      clientId: data.clientId.present ? data.clientId.value : this.clientId,
      propertyId: data.propertyId.present
          ? data.propertyId.value
          : this.propertyId,
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
    return (StringBuffer('PendingPackage(')
          ..write('clientId: $clientId, ')
          ..write('propertyId: $propertyId, ')
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
    createdAtLocal,
    syncStatus,
    errorMessage,
    remoteId,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PendingPackage &&
          other.clientId == this.clientId &&
          other.propertyId == this.propertyId &&
          other.createdAtLocal == this.createdAtLocal &&
          other.syncStatus == this.syncStatus &&
          other.errorMessage == this.errorMessage &&
          other.remoteId == this.remoteId);
}

class PendingPackagesCompanion extends UpdateCompanion<PendingPackage> {
  final Value<String> clientId;
  final Value<String> propertyId;
  final Value<DateTime> createdAtLocal;
  final Value<String> syncStatus;
  final Value<String?> errorMessage;
  final Value<String?> remoteId;
  final Value<int> rowid;
  const PendingPackagesCompanion({
    this.clientId = const Value.absent(),
    this.propertyId = const Value.absent(),
    this.createdAtLocal = const Value.absent(),
    this.syncStatus = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.remoteId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  PendingPackagesCompanion.insert({
    required String clientId,
    required String propertyId,
    required DateTime createdAtLocal,
    this.syncStatus = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.remoteId = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : clientId = Value(clientId),
       propertyId = Value(propertyId),
       createdAtLocal = Value(createdAtLocal);
  static Insertable<PendingPackage> custom({
    Expression<String>? clientId,
    Expression<String>? propertyId,
    Expression<DateTime>? createdAtLocal,
    Expression<String>? syncStatus,
    Expression<String>? errorMessage,
    Expression<String>? remoteId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (clientId != null) 'client_id': clientId,
      if (propertyId != null) 'property_id': propertyId,
      if (createdAtLocal != null) 'created_at_local': createdAtLocal,
      if (syncStatus != null) 'sync_status': syncStatus,
      if (errorMessage != null) 'error_message': errorMessage,
      if (remoteId != null) 'remote_id': remoteId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  PendingPackagesCompanion copyWith({
    Value<String>? clientId,
    Value<String>? propertyId,
    Value<DateTime>? createdAtLocal,
    Value<String>? syncStatus,
    Value<String?>? errorMessage,
    Value<String?>? remoteId,
    Value<int>? rowid,
  }) {
    return PendingPackagesCompanion(
      clientId: clientId ?? this.clientId,
      propertyId: propertyId ?? this.propertyId,
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
    return (StringBuffer('PendingPackagesCompanion(')
          ..write('clientId: $clientId, ')
          ..write('propertyId: $propertyId, ')
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
  late final $PendingPackagesTable pendingPackages = $PendingPackagesTable(
    this,
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    pendingAccessLogs,
    pendingIncidents,
    pendingPackages,
  ];
}

typedef $$PendingAccessLogsTableCreateCompanionBuilder =
    PendingAccessLogsCompanion Function({
      required String clientId,
      Value<String?> propertyId,
      required String tipo,
      Value<String> placas,
      Value<String?> nombreVisitante,
      Value<int> acompanantes,
      Value<String?> identificacion,
      Value<String?> autorizadoPor,
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
      Value<String?> nombreVisitante,
      Value<int> acompanantes,
      Value<String?> identificacion,
      Value<String?> autorizadoPor,
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

  ColumnFilters<String> get nombreVisitante => $composableBuilder(
    column: $table.nombreVisitante,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get acompanantes => $composableBuilder(
    column: $table.acompanantes,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get identificacion => $composableBuilder(
    column: $table.identificacion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get autorizadoPor => $composableBuilder(
    column: $table.autorizadoPor,
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

  ColumnOrderings<String> get nombreVisitante => $composableBuilder(
    column: $table.nombreVisitante,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get acompanantes => $composableBuilder(
    column: $table.acompanantes,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get identificacion => $composableBuilder(
    column: $table.identificacion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get autorizadoPor => $composableBuilder(
    column: $table.autorizadoPor,
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

  GeneratedColumn<String> get nombreVisitante => $composableBuilder(
    column: $table.nombreVisitante,
    builder: (column) => column,
  );

  GeneratedColumn<int> get acompanantes => $composableBuilder(
    column: $table.acompanantes,
    builder: (column) => column,
  );

  GeneratedColumn<String> get identificacion => $composableBuilder(
    column: $table.identificacion,
    builder: (column) => column,
  );

  GeneratedColumn<String> get autorizadoPor => $composableBuilder(
    column: $table.autorizadoPor,
    builder: (column) => column,
  );

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
                Value<String?> nombreVisitante = const Value.absent(),
                Value<int> acompanantes = const Value.absent(),
                Value<String?> identificacion = const Value.absent(),
                Value<String?> autorizadoPor = const Value.absent(),
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
                nombreVisitante: nombreVisitante,
                acompanantes: acompanantes,
                identificacion: identificacion,
                autorizadoPor: autorizadoPor,
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
                Value<String?> nombreVisitante = const Value.absent(),
                Value<int> acompanantes = const Value.absent(),
                Value<String?> identificacion = const Value.absent(),
                Value<String?> autorizadoPor = const Value.absent(),
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
                nombreVisitante: nombreVisitante,
                acompanantes: acompanantes,
                identificacion: identificacion,
                autorizadoPor: autorizadoPor,
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
      Value<String> tipo,
      Value<String?> propertyId,
      Value<String?> personaInvolucrada,
      Value<Uint8List?> fotoBytes,
      Value<String?> fotoNombre,
      Value<String?> fotoArchivoId,
      Value<bool> fotoDescartada,
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
      Value<String> tipo,
      Value<String?> propertyId,
      Value<String?> personaInvolucrada,
      Value<Uint8List?> fotoBytes,
      Value<String?> fotoNombre,
      Value<String?> fotoArchivoId,
      Value<bool> fotoDescartada,
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

  ColumnFilters<String> get tipo => $composableBuilder(
    column: $table.tipo,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get propertyId => $composableBuilder(
    column: $table.propertyId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get personaInvolucrada => $composableBuilder(
    column: $table.personaInvolucrada,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<Uint8List> get fotoBytes => $composableBuilder(
    column: $table.fotoBytes,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fotoNombre => $composableBuilder(
    column: $table.fotoNombre,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fotoArchivoId => $composableBuilder(
    column: $table.fotoArchivoId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get fotoDescartada => $composableBuilder(
    column: $table.fotoDescartada,
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

  ColumnOrderings<String> get tipo => $composableBuilder(
    column: $table.tipo,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get propertyId => $composableBuilder(
    column: $table.propertyId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get personaInvolucrada => $composableBuilder(
    column: $table.personaInvolucrada,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<Uint8List> get fotoBytes => $composableBuilder(
    column: $table.fotoBytes,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fotoNombre => $composableBuilder(
    column: $table.fotoNombre,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fotoArchivoId => $composableBuilder(
    column: $table.fotoArchivoId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get fotoDescartada => $composableBuilder(
    column: $table.fotoDescartada,
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

  GeneratedColumn<String> get tipo =>
      $composableBuilder(column: $table.tipo, builder: (column) => column);

  GeneratedColumn<String> get propertyId => $composableBuilder(
    column: $table.propertyId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get personaInvolucrada => $composableBuilder(
    column: $table.personaInvolucrada,
    builder: (column) => column,
  );

  GeneratedColumn<Uint8List> get fotoBytes =>
      $composableBuilder(column: $table.fotoBytes, builder: (column) => column);

  GeneratedColumn<String> get fotoNombre => $composableBuilder(
    column: $table.fotoNombre,
    builder: (column) => column,
  );

  GeneratedColumn<String> get fotoArchivoId => $composableBuilder(
    column: $table.fotoArchivoId,
    builder: (column) => column,
  );

  GeneratedColumn<bool> get fotoDescartada => $composableBuilder(
    column: $table.fotoDescartada,
    builder: (column) => column,
  );

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
                Value<String> tipo = const Value.absent(),
                Value<String?> propertyId = const Value.absent(),
                Value<String?> personaInvolucrada = const Value.absent(),
                Value<Uint8List?> fotoBytes = const Value.absent(),
                Value<String?> fotoNombre = const Value.absent(),
                Value<String?> fotoArchivoId = const Value.absent(),
                Value<bool> fotoDescartada = const Value.absent(),
                Value<DateTime> createdAtLocal = const Value.absent(),
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingIncidentsCompanion(
                clientId: clientId,
                descripcion: descripcion,
                fotoUrl: fotoUrl,
                tipo: tipo,
                propertyId: propertyId,
                personaInvolucrada: personaInvolucrada,
                fotoBytes: fotoBytes,
                fotoNombre: fotoNombre,
                fotoArchivoId: fotoArchivoId,
                fotoDescartada: fotoDescartada,
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
                Value<String> tipo = const Value.absent(),
                Value<String?> propertyId = const Value.absent(),
                Value<String?> personaInvolucrada = const Value.absent(),
                Value<Uint8List?> fotoBytes = const Value.absent(),
                Value<String?> fotoNombre = const Value.absent(),
                Value<String?> fotoArchivoId = const Value.absent(),
                Value<bool> fotoDescartada = const Value.absent(),
                required DateTime createdAtLocal,
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingIncidentsCompanion.insert(
                clientId: clientId,
                descripcion: descripcion,
                fotoUrl: fotoUrl,
                tipo: tipo,
                propertyId: propertyId,
                personaInvolucrada: personaInvolucrada,
                fotoBytes: fotoBytes,
                fotoNombre: fotoNombre,
                fotoArchivoId: fotoArchivoId,
                fotoDescartada: fotoDescartada,
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
typedef $$PendingPackagesTableCreateCompanionBuilder =
    PendingPackagesCompanion Function({
      required String clientId,
      required String propertyId,
      required DateTime createdAtLocal,
      Value<String> syncStatus,
      Value<String?> errorMessage,
      Value<String?> remoteId,
      Value<int> rowid,
    });
typedef $$PendingPackagesTableUpdateCompanionBuilder =
    PendingPackagesCompanion Function({
      Value<String> clientId,
      Value<String> propertyId,
      Value<DateTime> createdAtLocal,
      Value<String> syncStatus,
      Value<String?> errorMessage,
      Value<String?> remoteId,
      Value<int> rowid,
    });

class $$PendingPackagesTableFilterComposer
    extends Composer<_$AppDatabase, $PendingPackagesTable> {
  $$PendingPackagesTableFilterComposer({
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

class $$PendingPackagesTableOrderingComposer
    extends Composer<_$AppDatabase, $PendingPackagesTable> {
  $$PendingPackagesTableOrderingComposer({
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

class $$PendingPackagesTableAnnotationComposer
    extends Composer<_$AppDatabase, $PendingPackagesTable> {
  $$PendingPackagesTableAnnotationComposer({
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

class $$PendingPackagesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PendingPackagesTable,
          PendingPackage,
          $$PendingPackagesTableFilterComposer,
          $$PendingPackagesTableOrderingComposer,
          $$PendingPackagesTableAnnotationComposer,
          $$PendingPackagesTableCreateCompanionBuilder,
          $$PendingPackagesTableUpdateCompanionBuilder,
          (
            PendingPackage,
            BaseReferences<
              _$AppDatabase,
              $PendingPackagesTable,
              PendingPackage
            >,
          ),
          PendingPackage,
          PrefetchHooks Function()
        > {
  $$PendingPackagesTableTableManager(
    _$AppDatabase db,
    $PendingPackagesTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PendingPackagesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PendingPackagesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PendingPackagesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> clientId = const Value.absent(),
                Value<String> propertyId = const Value.absent(),
                Value<DateTime> createdAtLocal = const Value.absent(),
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingPackagesCompanion(
                clientId: clientId,
                propertyId: propertyId,
                createdAtLocal: createdAtLocal,
                syncStatus: syncStatus,
                errorMessage: errorMessage,
                remoteId: remoteId,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String clientId,
                required String propertyId,
                required DateTime createdAtLocal,
                Value<String> syncStatus = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<String?> remoteId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PendingPackagesCompanion.insert(
                clientId: clientId,
                propertyId: propertyId,
                createdAtLocal: createdAtLocal,
                syncStatus: syncStatus,
                errorMessage: errorMessage,
                remoteId: remoteId,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$PendingPackagesTable, PendingPackage>(table),
                  BaseReferences<
                    _$AppDatabase,
                    $PendingPackagesTable,
                    PendingPackage
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PendingPackagesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PendingPackagesTable,
      PendingPackage,
      $$PendingPackagesTableFilterComposer,
      $$PendingPackagesTableOrderingComposer,
      $$PendingPackagesTableAnnotationComposer,
      $$PendingPackagesTableCreateCompanionBuilder,
      $$PendingPackagesTableUpdateCompanionBuilder,
      (
        PendingPackage,
        BaseReferences<_$AppDatabase, $PendingPackagesTable, PendingPackage>,
      ),
      PendingPackage,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$PendingAccessLogsTableTableManager get pendingAccessLogs =>
      $$PendingAccessLogsTableTableManager(_db, _db.pendingAccessLogs);
  $$PendingIncidentsTableTableManager get pendingIncidents =>
      $$PendingIncidentsTableTableManager(_db, _db.pendingIncidents);
  $$PendingPackagesTableTableManager get pendingPackages =>
      $$PendingPackagesTableTableManager(_db, _db.pendingPackages);
}
