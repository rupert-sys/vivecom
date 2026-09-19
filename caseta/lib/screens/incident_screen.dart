import 'dart:async';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/foundation.dart' show Uint8List;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../db/app_database.dart';
import '../models/property.dart';
import '../services/property_service.dart';
import '../services/sync_service.dart';
import '../utils/dates.dart';
import '../widgets/estado_sync_badge.dart';

const _uuid = Uuid();

// Peso máximo que acepta el backend (10 MB). Con la compresión de abajo una foto pesa ~1 MB, pero se
// revisa igual por si el selector devuelve el original.
const int pesoMaximoDeLaFoto = 10 * 1024 * 1024;

class FotoCapturada {
  final String nombre;
  final Uint8List bytes;

  FotoCapturada({required this.nombre, required this.bytes});
}

enum OrigenDeLaFoto { camara, galeria }

// Inyectable para que las pruebas de widget no abran la cámara real (mismo patrón que AbrirUrl en la app residente).
typedef CapturarFoto = Future<FotoCapturada?> Function(OrigenDeLaFoto origen);

// Se reduce a 1600 px y calidad 80: una foto de teléfono pesa varios MB y la caseta puede tener poca
// señal. En iOS esto además convierte HEIC a JPEG.
Future<FotoCapturada?> capturarFotoReal(OrigenDeLaFoto origen) async {
  final foto = await ImagePicker().pickImage(
    source: origen == OrigenDeLaFoto.camara ? ImageSource.camera : ImageSource.gallery,
    maxWidth: 1600,
    maxHeight: 1600,
    imageQuality: 80,
  );
  if (foto == null) return null;
  return FotoCapturada(nombre: foto.name, bytes: await foto.readAsBytes());
}

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
  final CapturarFoto capturarFoto;

  const IncidentScreen({
    super.key,
    required this.token,
    required this.db,
    required this.propertyService,
    required this.syncService,
    this.capturarFoto = capturarFotoReal,
  });

  @override
  State<IncidentScreen> createState() => _IncidentScreenState();
}

class _IncidentScreenState extends State<IncidentScreen> {
  final _descripcionController = TextEditingController();
  final _personaController = TextEditingController();
  String _tipo = 'seguridad';
  String? _propertyId;
  List<Property> _propiedades = [];
  FotoCapturada? _foto;
  String? _errorFoto;

  @override
  void initState() {
    super.initState();
    _cargarPropiedades();
  }

  @override
  void dispose() {
    _descripcionController.dispose();
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

  Future<void> _tomarFoto(OrigenDeLaFoto origen) async {
    final foto = await widget.capturarFoto(origen);
    if (foto == null || !mounted) return;
    if (foto.bytes.length > pesoMaximoDeLaFoto) {
      setState(() => _errorFoto = 'La foto pesa más de 10 MB. Toma otra.');
      return;
    }
    setState(() {
      _foto = foto;
      _errorFoto = null;
    });
  }

  Future<void> _reportar() async {
    if (_descripcionController.text.trim().isEmpty) return;
    final foto = _foto;
    final persona = _personaController.text.trim();
    await widget.db
        .into(widget.db.pendingIncidents)
        .insert(
          PendingIncidentsCompanion.insert(
            clientId: _uuid.v4(),
            descripcion: _descripcionController.text.trim(),
            fotoBytes: Value(foto?.bytes),
            fotoNombre: Value(foto?.nombre),
            tipo: Value(_tipo),
            propertyId: Value(_propertyId),
            personaInvolucrada: Value(persona.isEmpty ? null : persona),
            createdAtLocal: DateTime.now(),
          ),
        );
    if (!mounted) return;
    _descripcionController.clear();
    _personaController.clear();
    setState(() {
      _tipo = 'seguridad';
      _propertyId = null;
      _foto = null;
      _errorFoto = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Incidencia registrada localmente. Se sincroniza en cuanto hay conexión.')),
    );
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
                  .map(
                    (e) => ButtonSegment(value: e.key, label: Text(e.value), icon: Icon(_iconosTipoIncidencia[e.key])),
                  )
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
            _buildFoto(),
            const SizedBox(height: 8),
            ElevatedButton(onPressed: _reportar, child: const Text('Reportar')),
          ],
        ),
      ),
    );
  }

  // La foto se queda en el teléfono mientras no hay conexión y se sube al sincronizar.
  Widget _buildFoto() {
    final foto = _foto;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (foto != null)
          Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.memory(
                  foto.bytes,
                  key: const Key('foto_previa'),
                  width: 72,
                  height: 72,
                  fit: BoxFit.cover,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(child: Text(foto.nombre, overflow: TextOverflow.ellipsis)),
              IconButton(
                key: const Key('quitar_foto'),
                icon: const Icon(Icons.close),
                tooltip: 'Quitar foto',
                onPressed: () => setState(() => _foto = null),
              ),
            ],
          )
        else
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  key: const Key('tomar_foto_button'),
                  onPressed: () => _tomarFoto(OrigenDeLaFoto.camara),
                  icon: const Icon(Icons.photo_camera),
                  label: const Text('Tomar foto'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  key: const Key('foto_galeria_button'),
                  onPressed: () => _tomarFoto(OrigenDeLaFoto.galeria),
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Galería'),
                ),
              ),
            ],
          ),
        if (_errorFoto != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              _errorFoto!,
              key: const Key('error_foto'),
              style: const TextStyle(color: Colors.red),
            ),
          ),
      ],
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
                  subtitle: Text(
                    [
                      _etiquetasTipoIncidencia[i.tipo] ?? i.tipo,
                      formatoHoraCorta(i.createdAtLocal),
                      if (i.fotoBytes != null || i.fotoArchivoId != null) 'con foto',
                      if (i.fotoDescartada) 'foto no enviada',
                    ].join(' · '),
                  ),
                  trailing: EstadoSyncBadge(estado: i.syncStatus),
                ),
              )
              .toList(),
        );
      },
    );
  }
}
