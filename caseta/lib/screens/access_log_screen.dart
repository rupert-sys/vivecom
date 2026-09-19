import 'dart:async';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../db/app_database.dart';
import '../models/access_log_entry.dart';
import '../models/parking_status.dart';
import '../models/property.dart';
import '../services/access_log_service.dart';
import '../services/api_client.dart';
import '../services/property_service.dart';
import '../services/sync_service.dart';
import '../utils/dates.dart';
import '../widgets/estado_sync_badge.dart';

const _uuid = Uuid();
const _tiposAcceso = ['residente', 'visitante', 'proveedor'];
const _etiquetasTipo = {'residente': 'Residente', 'visitante': 'Visitante', 'proveedor': 'Proveedor'};
// Reglamento Art. 17 V.3: el acceso requiere la autorización previa del
// condómino, o llamarle por teléfono si la visita es inesperada.
const _etiquetasAutorizacion = {
  'residente_previo': 'El residente avisó antes',
  'telefono': 'Le llamé al residente',
  'otro': 'Otro',
};

class AccessLogScreen extends StatefulWidget {
  final String token;
  final AppDatabase db;
  final PropertyService propertyService;
  final AccessLogService accessLogService;
  final SyncService syncService;

  const AccessLogScreen({
    super.key,
    required this.token,
    required this.db,
    required this.propertyService,
    required this.accessLogService,
    required this.syncService,
  });

  @override
  State<AccessLogScreen> createState() => _AccessLogScreenState();
}

class _AccessLogScreenState extends State<AccessLogScreen> {
  List<Property>? _propiedades;
  String _tipo = 'visitante';
  String? _propertyId;
  final _placasController = TextEditingController();
  final _nombreController = TextEditingController();
  final _identificacionController = TextEditingController();
  int _acompanantes = 0;
  String? _autorizadoPor;
  String? _errorFormulario;

  ParkingStatus? _estacionamiento;

  List<AccessLogEntry>? _abiertos;
  String? _errorAbiertos;
  bool _cargandoAbiertos = true;
  final Set<String> _registrandoSalida = {};

  @override
  void initState() {
    super.initState();
    _cargarPropiedades();
    _cargarAbiertos();
    _cargarEstacionamiento();
  }

  // Informativo: sin conexión simplemente no se muestra (la entrada se puede
  // registrar igual, el guardia decide con lo que ve en el lugar).
  Future<void> _cargarEstacionamiento() async {
    try {
      final estado = await widget.accessLogService.obtenerEstacionamiento(widget.token);
      if (!mounted) return;
      setState(() => _estacionamiento = estado);
    } catch (_) {
      if (!mounted) return;
      setState(() => _estacionamiento = null);
    }
  }

  @override
  void dispose() {
    _placasController.dispose();
    _nombreController.dispose();
    _identificacionController.dispose();
    super.dispose();
  }

  Future<void> _cargarPropiedades() async {
    try {
      final propiedades = await widget.propertyService.listarPropiedades(widget.token);
      if (!mounted) return;
      setState(() => _propiedades = propiedades);
    } catch (_) {
      // Sin conexión: se puede seguir registrando entradas sin vivienda
      // asociada (ej. proveedor) — el selector simplemente queda vacío.
      if (!mounted) return;
      setState(() => _propiedades = []);
    }
  }

  Future<void> _cargarAbiertos() async {
    setState(() {
      _cargandoAbiertos = true;
      _errorAbiertos = null;
    });
    try {
      final abiertos = await widget.accessLogService.listarAbiertos(widget.token);
      if (!mounted) return;
      setState(() => _abiertos = abiertos);
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorAbiertos = err is ApiException ? err.message : 'Sin conexión: no se pudieron cargar los accesos abiertos.');
    } finally {
      if (mounted) setState(() => _cargandoAbiertos = false);
    }
  }

  Future<void> _registrarEntrada() async {
    // Reglamento Art. 17 V.1: la bitácora lleva el nombre de quien entra (los
    // residentes se identifican solos, por eso a ellos no se les pide).
    final nombre = _nombreController.text.trim();
    if (_tipo != 'residente' && nombre.isEmpty) {
      setState(() => _errorFormulario = 'Anota el nombre de quien entra.');
      return;
    }
    final identificacion = _identificacionController.text.trim();
    final placas = _placasController.text.split(',').map((p) => p.trim()).where((p) => p.isNotEmpty).toList();
    await widget.db
        .into(widget.db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(
            clientId: _uuid.v4(),
            propertyId: Value(_propertyId),
            tipo: _tipo,
            placas: Value(_placasEnJson(placas)),
            nombreVisitante: Value(nombre.isEmpty ? null : nombre),
            acompanantes: Value(_acompanantes),
            identificacion: Value(identificacion.isEmpty ? null : identificacion),
            autorizadoPor: Value(_autorizadoPor),
            createdAtLocal: DateTime.now(),
          ),
        );
    if (!mounted) return;
    setState(() {
      _propertyId = null;
      _placasController.clear();
      _nombreController.clear();
      _identificacionController.clear();
      _acompanantes = 0;
      _autorizadoPor = null;
      _errorFormulario = null;
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Entrada registrada localmente. Se sincroniza en cuanto hay conexión.')));
    unawaited(widget.syncService.sincronizarPendientes());
  }

  String _placasEnJson(List<String> placas) => '[${placas.map((p) => '"$p"').join(',')}]';

  Future<void> _registrarSalida(String accessLogId) async {
    setState(() => _registrandoSalida.add(accessLogId));
    try {
      await widget.accessLogService.registrarSalida(accessLogId, widget.token);
      await _cargarAbiertos();
      await _cargarEstacionamiento();
    } catch (err) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err is ApiException ? err.message : 'No se pudo registrar la salida.')),
      );
    } finally {
      if (mounted) setState(() => _registrandoSalida.remove(accessLogId));
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {
        await Future.wait([_cargarAbiertos(), _cargarEstacionamiento()]);
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildEstacionamiento(),
          _buildFormularioEntrada(),
          const SizedBox(height: 24),
          Text('Accesos abiertos (sin salida)', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildAbiertos(),
          const SizedBox(height: 24),
          Text('Cola de sincronización', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildColaLocal(),
        ],
      ),
    );
  }

  Widget _buildEstacionamiento() {
    final estado = _estacionamiento;
    if (estado == null || estado.totalCajones == 0) return const SizedBox.shrink();
    final lleno = estado.libres == 0;
    return Card(
      key: const Key('estacionamiento_visitas'),
      color: (lleno ? Colors.red : Colors.green).withValues(alpha: 0.1),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Icon(Icons.local_parking, color: lleno ? Colors.red : Colors.green),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Cajones de visitas: ${estado.libres} libres de ${estado.totalCajones}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  if (lleno) const Text('Llenos: solo pasa si el visitado tiene lugar propio.'),
                  if (estado.excedidos > 0)
                    Text(
                      '${estado.excedidos} ${estado.excedidos == 1 ? 'vehículo rebasó' : 'vehículos rebasaron'} las ${estado.horasMaximas} h permitidas.',
                      style: const TextStyle(color: Colors.orange),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFormularioEntrada() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Registrar entrada'),
            const SizedBox(height: 8),
            DropdownButton<String>(
              key: const Key('tipo_dropdown'),
              value: _tipo,
              items: _tiposAcceso.map((t) => DropdownMenuItem(value: t, child: Text(_etiquetasTipo[t]!))).toList(),
              onChanged: (valor) => setState(() {
                _tipo = valor!;
                _errorFormulario = null;
              }),
            ),
            const SizedBox(height: 8),
            DropdownButton<String?>(
              key: const Key('vivienda_dropdown'),
              value: _propertyId,
              hint: const Text('Vivienda (opcional)'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Sin vivienda asociada')),
                ...(_propiedades ?? []).map((p) => DropdownMenuItem<String?>(value: p.id, child: Text(p.identificador))),
              ],
              onChanged: (valor) => setState(() => _propertyId = valor),
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('placas_field'),
              controller: _placasController,
              decoration: const InputDecoration(labelText: 'Placas (separadas por coma, opcional)'),
            ),
            if (_tipo != 'residente') ...[
              const SizedBox(height: 8),
              TextField(
                key: const Key('nombre_field'),
                controller: _nombreController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Nombre de quien entra'),
              ),
              const SizedBox(height: 8),
              TextField(
                key: const Key('identificacion_field'),
                controller: _identificacionController,
                decoration: const InputDecoration(labelText: 'Identificación que dejó (opcional)'),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Expanded(child: Text('Acompañantes')),
                  IconButton(
                    key: const Key('acompanantes_menos'),
                    icon: const Icon(Icons.remove_circle_outline),
                    onPressed: _acompanantes == 0 ? null : () => setState(() => _acompanantes--),
                  ),
                  Text('$_acompanantes', key: const Key('acompanantes_valor')),
                  IconButton(
                    key: const Key('acompanantes_mas'),
                    icon: const Icon(Icons.add_circle_outline),
                    onPressed: () => setState(() => _acompanantes++),
                  ),
                ],
              ),
              DropdownButton<String?>(
                key: const Key('autorizacion_dropdown'),
                value: _autorizadoPor,
                isExpanded: true,
                hint: const Text('¿Quién autorizó el acceso?'),
                items: [
                  const DropdownMenuItem<String?>(value: null, child: Text('Sin especificar')),
                  ..._etiquetasAutorizacion.entries.map((e) => DropdownMenuItem<String?>(value: e.key, child: Text(e.value))),
                ],
                onChanged: (valor) => setState(() => _autorizadoPor = valor),
              ),
            ],
            if (_errorFormulario != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_errorFormulario!, key: const Key('error_formulario'), style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 8),
            ElevatedButton(onPressed: _registrarEntrada, child: const Text('Registrar entrada')),
          ],
        ),
      ),
    );
  }

  Widget _buildColaLocal() {
    return StreamBuilder<List<PendingAccessLog>>(
      stream: widget.db.watchAccesos(),
      builder: (context, snapshot) {
        final registros = snapshot.data ?? [];
        if (registros.isEmpty) {
          return const Text('Sin registros en cola.');
        }
        return Column(
          children: registros
              .map(
                (r) => ListTile(
                  dense: true,
                  title: Text('${_etiquetasTipo[r.tipo] ?? r.tipo}${r.nombreVisitante != null ? ' · ${r.nombreVisitante}' : ''} · ${formatoHoraCorta(r.createdAtLocal)}'),
                  trailing: EstadoSyncBadge(estado: r.syncStatus),
                ),
              )
              .toList(),
        );
      },
    );
  }

  Widget? _detalleAcceso(AccessLogEntry a) {
    final partes = [
      if (a.placas.isNotEmpty) a.placas.join(', '),
      if (a.acompanantes > 0) '${a.acompanantes} ${a.acompanantes == 1 ? 'acompañante' : 'acompañantes'}',
    ];
    return partes.isEmpty ? null : Text(partes.join(' · '));
  }

  Widget _buildAbiertos() {
    if (_cargandoAbiertos && _abiertos == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorAbiertos != null && _abiertos == null) {
      return Text(_errorAbiertos!, style: const TextStyle(color: Colors.orange));
    }
    final abiertos = _abiertos ?? [];
    if (abiertos.isEmpty) {
      return const Text('No hay accesos abiertos.');
    }
    return Column(
      children: abiertos
          .map(
            (a) => ListTile(
              title: Text(
                '${_etiquetasTipo[a.tipo] ?? a.tipo}${a.nombreVisitante != null ? ' · ${a.nombreVisitante}' : ''} · entrada ${formatoHoraCorta(a.horaEntrada)}',
              ),
              subtitle: _detalleAcceso(a),
              trailing: _registrandoSalida.contains(a.id)
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : TextButton(onPressed: () => _registrarSalida(a.id), child: const Text('Salida')),
            ),
          )
          .toList(),
    );
  }
}
