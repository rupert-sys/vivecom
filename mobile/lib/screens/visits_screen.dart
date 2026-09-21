import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';

import '../models/visit.dart';
import '../services/api_client.dart';
import '../services/visit_service.dart';
import '../utils/dates.dart';

// Manda el código a la visita: la imagen del QR (lo que escanea el guardia) y un texto con el código por si
// no se puede escanear. Se inyecta para poder probar la pantalla sin abrir la hoja de compartir del sistema.
typedef CompartirCodigo = Future<void> Function({
  required String codigo,
  required Uint8List imagen,
  required String texto,
});

const _nombreImagenQr = 'codigo-de-visita.png';

Future<void> compartirConLaHojaDelSistema({required String codigo, required Uint8List imagen, required String texto}) {
  return SharePlus.instance.share(
    ShareParams(
      text: texto,
      subject: 'Código de visita',
      files: [XFile.fromData(imagen, mimeType: 'image/png', name: _nombreImagenQr)],
      fileNameOverrides: [_nombreImagenQr],
    ),
  );
}

/// El QR como PNG con fondo blanco y margen (una visita lo abre en el chat, en modo oscuro también).
Future<Uint8List> imagenDelQr(String codigo, {double lado = 720, double margen = 60}) async {
  final grabador = ui.PictureRecorder();
  final lienzo = Canvas(grabador);
  lienzo.drawRect(Rect.fromLTWH(0, 0, lado, lado), Paint()..color = Colors.white);
  lienzo.translate(margen, margen);
  QrPainter(data: codigo, version: QrVersions.auto).paint(lienzo, Size(lado - 2 * margen, lado - 2 * margen));
  final imagen = await grabador.endRecording().toImage(lado.toInt(), lado.toInt());
  final bytes = await imagen.toByteData(format: ui.ImageByteFormat.png);
  return bytes!.buffer.asUint8List();
}

// Visitas y paquetes de la vivienda: el residente genera el código (QR de un
// solo uso) que le da a su visita para entrar sin que el guardia tenga que
// llamarle, y ve qué paquetes esperan en la caseta (HU-S02, HU-S05).
class VisitsScreen extends StatefulWidget {
  final String token;
  final VisitService visitService;
  final CompartirCodigo compartir;

  const VisitsScreen({
    super.key,
    required this.token,
    required this.visitService,
    this.compartir = compartirConLaHojaDelSistema,
  });

  @override
  State<VisitsScreen> createState() => _VisitsScreenState();
}

class _VisitsScreenState extends State<VisitsScreen> {
  List<VisitorQr>? _codigos;
  List<PackageItem>? _paquetes;
  String? _errorCodigos;
  String? _errorPaquetes;
  bool _cargando = true;

  VisitorQr? _recienGenerado;
  bool _generando = false;
  String? _errorGenerar;
  bool _compartiendo = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _cargando = true);
    // Cada sección falla por separado: que no carguen los paquetes no debe
    // impedir generar el código de una visita.
    await Future.wait([_cargarCodigos(), _cargarPaquetes()]);
    if (mounted) setState(() => _cargando = false);
  }

  Future<void> _cargarCodigos() async {
    try {
      final codigos = await widget.visitService.listarMisCodigos(widget.token);
      if (!mounted) return;
      setState(() {
        _codigos = codigos;
        _errorCodigos = null;
      });
    } catch (err) {
      if (mounted) {
        setState(() => _errorCodigos = err is ApiException ? err.message : 'No se pudieron cargar tus códigos.');
      }
    }
  }

  Future<void> _cargarPaquetes() async {
    try {
      final paquetes = await widget.visitService.listarMisPaquetes(widget.token);
      if (!mounted) return;
      setState(() {
        _paquetes = paquetes;
        _errorPaquetes = null;
      });
    } catch (err) {
      if (mounted) {
        setState(() => _errorPaquetes = err is ApiException ? err.message : 'No se pudieron cargar tus paquetes.');
      }
    }
  }

  Future<void> _generar() async {
    setState(() {
      _generando = true;
      _errorGenerar = null;
    });
    try {
      final codigo = await widget.visitService.generarCodigoDeVisita(widget.token);
      if (!mounted) return;
      setState(() => _recienGenerado = codigo);
      await _cargarCodigos();
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorGenerar = err is ApiException ? err.message : 'No se pudo generar el código.');
    } finally {
      if (mounted) setState(() => _generando = false);
    }
  }

  static String _pad(int n) => n.toString().padLeft(2, '0');

  String _fechaHora(DateTime fecha) {
    final local = fecha.toLocal();
    return '${formatoFechaCorta(local)} ${_pad(local.hour)}:${_pad(local.minute)}';
  }

  // Sin Scaffold/AppBar propios: ver la nota en announcements_screen.dart.
  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _cargar,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildGenerador(),
          const SizedBox(height: 24),
          Text('Mis códigos', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ..._buildCodigos(),
          const SizedBox(height: 24),
          Text('Paquetes', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ..._buildPaquetes(),
        ],
      ),
    );
  }

  Future<void> _compartir(VisitorQr codigo) async {
    setState(() => _compartiendo = true);
    try {
      final imagen = await imagenDelQr(codigo.codigo);
      await widget.compartir(
        codigo: codigo.codigo,
        imagen: imagen,
        texto:
            'Código de visita (sirve una sola vez): ${codigo.codigo}\n'
            'Enséñalo en la caseta al llegar: el guardia escanea el QR y te deja pasar.',
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No se pudo compartir el código.')));
      }
    } finally {
      if (mounted) setState(() => _compartiendo = false);
    }
  }

  Widget _buildGenerador() {
    final codigo = _recienGenerado;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Código para tu visita', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
              'Genera un código y enséñaselo (o mándaselo) a tu visita: el guardia lo escanea en la caseta '
              'y la deja pasar. Sirve una sola vez.',
            ),
            const SizedBox(height: 12),
            if (codigo != null) ...[
              Center(
                child: Container(
                  key: const Key('qr_generado'),
                  color: Colors.white,
                  padding: const EdgeInsets.all(8),
                  child: QrImageView(key: Key('qr_${codigo.codigo}'), data: codigo.codigo, size: 200),
                ),
              ),
              const SizedBox(height: 8),
              Center(child: SelectableText(codigo.codigo, key: const Key('codigo_generado'))),
              const SizedBox(height: 8),
              Center(
                child: OutlinedButton.icon(
                  key: const Key('compartir_codigo'),
                  onPressed: _compartiendo ? null : () => _compartir(codigo),
                  icon: const Icon(Icons.share),
                  label: Text(_compartiendo ? 'Preparando…' : 'Compartir código'),
                ),
              ),
              const SizedBox(height: 12),
            ],
            if (_errorGenerar != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_errorGenerar!, style: const TextStyle(color: Colors.red)),
              ),
            ElevatedButton.icon(
              onPressed: _generando ? null : _generar,
              icon: const Icon(Icons.qr_code),
              label: Text(
                _generando ? 'Generando…' : (codigo == null ? 'Generar código de visita' : 'Generar otro código'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildCodigos() {
    if (_errorCodigos != null) return [Text(_errorCodigos!, style: const TextStyle(color: Colors.red))];
    final codigos = _codigos;
    if (codigos == null) return [if (_cargando) const Center(child: CircularProgressIndicator())];
    if (codigos.isEmpty) return [const Text('Todavía no has generado códigos.')];
    return codigos
        .map(
          (c) => ListTile(
            key: Key('codigo_${c.id}'),
            leading: Icon(c.usado ? Icons.check_circle : Icons.qr_code_2, color: c.usado ? Colors.grey : Colors.green),
            title: Text(c.usado ? 'Usado' : 'Sin usar'),
            subtitle: Text(
              c.usado && c.fechaUsado != null
                  ? 'Generado ${_fechaHora(c.fechaGenerado)} · usado ${_fechaHora(c.fechaUsado!)}'
                  : 'Generado ${_fechaHora(c.fechaGenerado)}',
            ),
            onTap: c.usado ? null : () => setState(() => _recienGenerado = c),
          ),
        )
        .toList();
  }

  List<Widget> _buildPaquetes() {
    if (_errorPaquetes != null) return [Text(_errorPaquetes!, style: const TextStyle(color: Colors.red))];
    final paquetes = _paquetes;
    if (paquetes == null) return [if (_cargando) const Center(child: CircularProgressIndicator())];
    if (paquetes.isEmpty) return [const Text('No tienes paquetes en la caseta.')];
    return paquetes
        .map(
          (p) => ListTile(
            key: Key('paquete_${p.id}'),
            leading: Icon(
              p.recogido ? Icons.inventory_2_outlined : Icons.inventory_2,
              color: p.recogido ? Colors.grey : Colors.orange,
            ),
            title: Text(p.recogido ? 'Recogido' : 'Por recoger en la caseta'),
            subtitle: Text(
              p.recogido
                  ? 'Llegó ${_fechaHora(p.fechaLlegada)} · recogido ${_fechaHora(p.fechaRecogido!)}'
                  : 'Llegó ${_fechaHora(p.fechaLlegada)}',
            ),
          ),
        )
        .toList();
  }
}
