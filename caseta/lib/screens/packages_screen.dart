import 'dart:async';

import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../db/app_database.dart';
import '../models/package_entry.dart';
import '../models/property.dart';
import '../services/api_client.dart';
import '../services/package_service.dart';
import '../services/property_service.dart';
import '../services/sync_service.dart';
import '../utils/dates.dart';
import '../widgets/estado_sync_badge.dart';

const _uuid = Uuid();

// Paquetería (HU-S05): el guardia registra la llegada y el residente recibe el
// aviso en su app (más WhatsApp/SMS de respaldo); al entregarlo se cierra el
// registro y se le avisa que ya lo recogió. La llegada se encola offline como
// un acceso — es lo que no puede perderse; la entrega requiere conexión.
class PackagesScreen extends StatefulWidget {
  final String token;
  final AppDatabase db;
  final PropertyService propertyService;
  final PackageService packageService;
  final SyncService syncService;

  const PackagesScreen({
    super.key,
    required this.token,
    required this.db,
    required this.propertyService,
    required this.packageService,
    required this.syncService,
  });

  @override
  State<PackagesScreen> createState() => _PackagesScreenState();
}

class _PackagesScreenState extends State<PackagesScreen> {
  List<Property> _propiedades = [];
  String? _propertyId;
  String? _errorFormulario;

  List<PackageEntry>? _enCaseta;
  String? _errorEnCaseta;
  bool _cargando = true;
  final Set<String> _entregando = {};

  @override
  void initState() {
    super.initState();
    _cargarPropiedades();
    _cargarEnCaseta();
  }

  Future<void> _cargarPropiedades() async {
    try {
      final propiedades = await widget.propertyService.listarPropiedades(widget.token);
      if (!mounted) return;
      setState(() => _propiedades = propiedades);
    } catch (_) {
      // Sin conexión no hay lista de viviendas: el formulario avisa que hace falta.
    }
  }

  Future<void> _cargarEnCaseta() async {
    setState(() {
      _cargando = true;
      _errorEnCaseta = null;
    });
    try {
      final paquetes = await widget.packageService.listarEnCaseta(widget.token);
      if (!mounted) return;
      setState(() => _enCaseta = paquetes);
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorEnCaseta = err is ApiException ? err.message : 'Sin conexión: no se pudo cargar la lista de paquetes.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  String _nombreDeVivienda(String propertyId) {
    for (final p in _propiedades) {
      if (p.id == propertyId) return p.identificador;
    }
    return 'Vivienda desconocida';
  }

  Future<void> _registrarLlegada() async {
    final propertyId = _propertyId;
    if (propertyId == null) {
      setState(() => _errorFormulario = 'Elige la vivienda a la que llegó el paquete.');
      return;
    }
    await widget.db
        .into(widget.db.pendingPackages)
        .insert(PendingPackagesCompanion.insert(clientId: _uuid.v4(), propertyId: propertyId, createdAtLocal: DateTime.now()));
    if (!mounted) return;
    setState(() {
      _propertyId = null;
      _errorFormulario = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Paquete registrado. Se le avisa al residente en cuanto haya conexión.')),
    );
    await widget.syncService.sincronizarPendientes();
    await _cargarEnCaseta();
  }

  Future<void> _entregar(PackageEntry paquete) async {
    setState(() => _entregando.add(paquete.id));
    try {
      await widget.packageService.marcarEntregado(paquete.id, widget.token);
      await _cargarEnCaseta();
    } catch (err) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err is ApiException ? err.message : 'No se pudo registrar la entrega.')),
      );
    } finally {
      if (mounted) setState(() => _entregando.remove(paquete.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _cargarEnCaseta,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildFormulario(),
          const SizedBox(height: 24),
          Text('Cola de sincronización', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildColaLocal(),
          const SizedBox(height: 24),
          Text('Paquetes en la caseta', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildEnCaseta(),
        ],
      ),
    );
  }

  Widget _buildFormulario() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Registrar llegada de paquete'),
            const SizedBox(height: 8),
            DropdownButton<String?>(
              key: const Key('paquete_vivienda_dropdown'),
              value: _propertyId,
              isExpanded: true,
              hint: const Text('Vivienda destinataria'),
              items: _propiedades.map((p) => DropdownMenuItem<String?>(value: p.id, child: Text(p.identificador))).toList(),
              onChanged: (valor) => setState(() {
                _propertyId = valor;
                _errorFormulario = null;
              }),
            ),
            if (_errorFormulario != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(_errorFormulario!, key: const Key('error_paquete'), style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 8),
            ElevatedButton.icon(
              onPressed: _registrarLlegada,
              icon: const Icon(Icons.inventory_2),
              label: const Text('Registrar paquete'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildColaLocal() {
    return StreamBuilder<List<PendingPackage>>(
      stream: widget.db.watchPaquetes(),
      builder: (context, snapshot) {
        final registros = snapshot.data ?? [];
        if (registros.isEmpty) return const Text('Sin paquetes en cola.');
        return Column(
          children: registros
              .map(
                (r) => ListTile(
                  dense: true,
                  title: Text('${_nombreDeVivienda(r.propertyId)} · ${formatoHoraCorta(r.createdAtLocal)}'),
                  trailing: EstadoSyncBadge(estado: r.syncStatus),
                ),
              )
              .toList(),
        );
      },
    );
  }

  Widget _buildEnCaseta() {
    if (_cargando && _enCaseta == null) return const Center(child: CircularProgressIndicator());
    if (_errorEnCaseta != null && _enCaseta == null) {
      return Text(_errorEnCaseta!, style: const TextStyle(color: Colors.orange));
    }
    final paquetes = _enCaseta ?? [];
    if (paquetes.isEmpty) return const Text('No hay paquetes esperando a su residente.');
    return Column(
      children: paquetes
          .map(
            (p) => ListTile(
              key: Key('paquete_${p.id}'),
              leading: const Icon(Icons.inventory_2),
              title: Text(_nombreDeVivienda(p.propertyId)),
              subtitle: Text('Llegó a las ${formatoHoraCorta(p.fechaLlegada)}'),
              trailing: _entregando.contains(p.id)
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : TextButton(onPressed: () => _entregar(p), child: const Text('Entregado')),
            ),
          )
          .toList(),
    );
  }
}
