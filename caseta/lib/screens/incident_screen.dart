import 'dart:async';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../db/app_database.dart';
import '../models/property.dart';
import '../services/property_service.dart';
import '../services/sync_service.dart';
import '../utils/dates.dart';
import '../widgets/estado_sync_badge.dart';

const _uuid = Uuid();
// La caseta levanta incidentes de seguridad y reporta fallas de mantenimiento
// (una luminaria fundida, el portón). Reportar la falla no es administrar el
// mantenimiento: el administrador y el comité le dan seguimiento.
const _etiquetasTipoIncidencia = {'seguridad': 'Seguridad', 'mantenimiento': 'Mantenimiento', 'otro': 'Otro'};
const _iconosTipoIncidencia = {
  'seguridad': Icons.shield_outlined,
  'mantenimiento': Icons.build_outlined,
  'otro': Icons.report_problem_outlined,
};

class IncidentScreen extends StatefulWidget {
  final String token;
  final AppDatabase db;
  final PropertyService propertyService;
  final SyncService syncService;

  const IncidentScreen({
    super.key,
    required this.token,
    required this.db,
    required this.propertyService,
    required this.syncService,
  });

  @override
  State<IncidentScreen> createState() => _IncidentScreenState();
}

class _IncidentScreenState extends State<IncidentScreen> {
  final _descripcionController = TextEditingController();
  final _fotoUrlController = TextEditingController();
  final _personaController = TextEditingController();
  String _tipo = 'seguridad';
  String? _propertyId;
  List<Property> _propiedades = [];

  @override
  void initState() {
    super.initState();
    _cargarPropiedades();
  }

  @override
  void dispose() {
    _descripcionController.dispose();
    _fotoUrlController.dispose();
    _personaController.dispose();
    super.dispose();
  }

  Future<void> _cargarPropiedades() async {
    try {
      final propiedades = await widget.propertyService.listarPropiedades(widget.token);
      if (!mounted) return;
      setState(() => _propiedades = propiedades);
    } catch (_) {
      // Sin conexión: se puede reportar igual, solo sin elegir la casa de la lista.
    }
  }

  Future<void> _reportar() async {
    if (_descripcionController.text.trim().isEmpty) return;
    final fotoUrl = _fotoUrlController.text.trim();
    final persona = _personaController.text.trim();
    await widget.db
        .into(widget.db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(
            clientId: _uuid.v4(),
            descripcion: _descripcionController.text.trim(),
            fotoUrl: Value(fotoUrl.isEmpty ? null : fotoUrl),
            tipo: Value(_tipo),
            propertyId: Value(_propertyId),
            personaInvolucrada: Value(persona.isEmpty ? null : persona),
            createdAtLocal: DateTime.now(),
          ),
        );
    if (!mounted) return;
    _descripcionController.clear();
    _fotoUrlController.clear();
    _personaController.clear();
    setState(() {
      _tipo = 'seguridad';
      _propertyId = null;
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Incidencia registrada localmente. Se sincroniza en cuanto hay conexión.')));
    unawaited(widget.syncService.sincronizarPendientes());
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildFormulario(),
        const SizedBox(height: 24),
        Text('Cola de sincronización', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _buildColaLocal(),
      ],
    );
  }

  Widget _buildFormulario() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Reportar incidencia'),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              key: const Key('tipo_incidencia'),
              segments: _etiquetasTipoIncidencia.entries
                  .map((e) => ButtonSegment(value: e.key, label: Text(e.value), icon: Icon(_iconosTipoIncidencia[e.key])))
                  .toList(),
              selected: {_tipo},
              onSelectionChanged: (seleccion) => setState(() => _tipo = seleccion.first),
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('descripcion_field'),
              controller: _descripcionController,
              decoration: const InputDecoration(labelText: 'Descripción'),
              maxLines: 3,
            ),
            const SizedBox(height: 8),
            DropdownButton<String?>(
              key: const Key('incidente_vivienda_dropdown'),
              value: _propertyId,
              isExpanded: true,
              hint: const Text('Casa involucrada (opcional)'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Sin casa involucrada')),
                ..._propiedades.map((p) => DropdownMenuItem<String?>(value: p.id, child: Text(p.identificador))),
              ],
              onChanged: (valor) => setState(() => _propertyId = valor),
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('persona_field'),
              controller: _personaController,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Persona involucrada, interna o externa (opcional)'),
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('foto_url_field'),
              controller: _fotoUrlController,
              decoration: const InputDecoration(labelText: 'URL de foto (opcional)'),
            ),
            const SizedBox(height: 8),
            ElevatedButton(onPressed: _reportar, child: const Text('Reportar')),
          ],
        ),
      ),
    );
  }

  Widget _buildColaLocal() {
    return StreamBuilder<List<PendingIncident>>(
      stream: widget.db.watchIncidencias(),
      builder: (context, snapshot) {
        final incidencias = snapshot.data ?? [];
        if (incidencias.isEmpty) {
          return const Text('Sin incidencias en cola.');
        }
        return Column(
          children: incidencias
              .map(
                (i) => ListTile(
                  dense: true,
                  leading: Icon(_iconosTipoIncidencia[i.tipo] ?? Icons.report_problem_outlined),
                  title: Text(i.descripcion),
                  subtitle: Text('${_etiquetasTipoIncidencia[i.tipo] ?? i.tipo} · ${formatoHoraCorta(i.createdAtLocal)}'),
                  trailing: EstadoSyncBadge(estado: i.syncStatus),
                ),
              )
              .toList(),
        );
      },
    );
  }
}
