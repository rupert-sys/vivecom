import 'dart:async';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../db/app_database.dart';
import '../models/access_log_entry.dart';
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

  List<AccessLogEntry>? _abiertos;
  String? _errorAbiertos;
  bool _cargandoAbiertos = true;
  final Set<String> _registrandoSalida = {};

  @override
  void initState() {
    super.initState();
    _cargarPropiedades();
    _cargarAbiertos();
  }

  @override
  void dispose() {
    _placasController.dispose();
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
    final placas = _placasController.text.split(',').map((p) => p.trim()).where((p) => p.isNotEmpty).toList();
    await widget.db
        .into(widget.db.pendingAccessLogs)
        .insert(
          PendingAccessLogsCompanion.insert(
            clientId: _uuid.v4(),
            propertyId: Value(_propertyId),
            tipo: _tipo,
            placas: Value(_placasEnJson(placas)),
            createdAtLocal: DateTime.now(),
          ),
        );
    if (!mounted) return;
    setState(() {
      _propertyId = null;
      _placasController.clear();
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
      onRefresh: _cargarAbiertos,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildFormularioEntrada(),
          const SizedBox(height: 24),
          Text('Cola de sincronización', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildColaLocal(),
          const SizedBox(height: 24),
          Text('Accesos abiertos (sin salida)', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildAbiertos(),
        ],
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
              onChanged: (valor) => setState(() => _tipo = valor!),
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
                  title: Text('${_etiquetasTipo[r.tipo] ?? r.tipo} · ${formatoHoraCorta(r.createdAtLocal)}'),
                  trailing: EstadoSyncBadge(estado: r.syncStatus),
                ),
              )
              .toList(),
        );
      },
    );
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
              title: Text('${_etiquetasTipo[a.tipo] ?? a.tipo} · entrada ${formatoHoraCorta(a.horaEntrada)}'),
              subtitle: a.placas.isNotEmpty ? Text(a.placas.join(', ')) : null,
              trailing: _registrandoSalida.contains(a.id)
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : TextButton(onPressed: () => _registrarSalida(a.id), child: const Text('Salida')),
            ),
          )
          .toList(),
    );
  }
}
