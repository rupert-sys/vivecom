import 'dart:async';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../db/app_database.dart';
import '../services/sync_service.dart';
import '../utils/dates.dart';
import '../widgets/estado_sync_badge.dart';

const _uuid = Uuid();

class IncidentScreen extends StatefulWidget {
  final AppDatabase db;
  final SyncService syncService;

  const IncidentScreen({super.key, required this.db, required this.syncService});

  @override
  State<IncidentScreen> createState() => _IncidentScreenState();
}

class _IncidentScreenState extends State<IncidentScreen> {
  final _descripcionController = TextEditingController();
  final _fotoUrlController = TextEditingController();

  @override
  void dispose() {
    _descripcionController.dispose();
    _fotoUrlController.dispose();
    super.dispose();
  }

  Future<void> _reportar() async {
    if (_descripcionController.text.trim().isEmpty) return;
    final fotoUrl = _fotoUrlController.text.trim();
    await widget.db
        .into(widget.db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(
            clientId: _uuid.v4(),
            descripcion: _descripcionController.text.trim(),
            fotoUrl: Value(fotoUrl.isEmpty ? null : fotoUrl),
            createdAtLocal: DateTime.now(),
          ),
        );
    if (!mounted) return;
    _descripcionController.clear();
    _fotoUrlController.clear();
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
            TextField(
              key: const Key('descripcion_field'),
              controller: _descripcionController,
              decoration: const InputDecoration(labelText: 'Descripción'),
              maxLines: 3,
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
                  title: Text(i.descripcion),
                  subtitle: Text(formatoHoraCorta(i.createdAtLocal)),
                  trailing: EstadoSyncBadge(estado: i.syncStatus),
                ),
              )
              .toList(),
        );
      },
    );
  }
}
