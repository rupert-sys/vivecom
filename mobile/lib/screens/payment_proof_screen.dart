import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../models/payment_proof.dart';
import '../services/api_client.dart';
import '../services/payment_proof_service.dart';
import '../utils/dates.dart';
import 'expenses_screen.dart' show AbrirUrl, abrirUrlReal;

// Peso máximo que acepta el backend (10 MB): se revisa aquí para no subir en vano un archivo enorme.
const int pesoMaximoDelComprobante = 10 * 1024 * 1024;

class ArchivoElegido {
  final String nombre;
  final List<int> bytes;

  ArchivoElegido({required this.nombre, required this.bytes});
}

enum OrigenDelArchivo { foto, pdf }

// Inyectable para que las pruebas de widget no abran el selector de archivos real del sistema
// (mismo patrón que AbrirUrl y CompartirPdf).
typedef SeleccionarArchivo = Future<ArchivoElegido?> Function(OrigenDelArchivo origen);

Future<ArchivoElegido?> seleccionarArchivoReal(OrigenDelArchivo origen) async {
  final archivo = await FilePicker.pickFile(
    type: origen == OrigenDelArchivo.foto ? FileType.image : FileType.custom,
    allowedExtensions: origen == OrigenDelArchivo.pdf ? ['pdf'] : null,
  );
  if (archivo == null) return null;
  return ArchivoElegido(nombre: archivo.name, bytes: await archivo.readAsBytes());
}

// "Ya pagué": el residente adjunta la captura o el PDF de su transferencia. No registra el pago
// por sí solo — tesorería lo revisa; aquí se ve en qué va cada comprobante.
class PaymentProofScreen extends StatefulWidget {
  final String token;
  final PaymentProofService proofService;
  final SeleccionarArchivo seleccionarArchivo;
  final AbrirUrl abrirUrl;

  const PaymentProofScreen({
    super.key,
    required this.token,
    required this.proofService,
    this.seleccionarArchivo = seleccionarArchivoReal,
    this.abrirUrl = abrirUrlReal,
  });

  @override
  State<PaymentProofScreen> createState() => _PaymentProofScreenState();
}

class _PaymentProofScreenState extends State<PaymentProofScreen> {
  List<PaymentProof>? _comprobantes;
  String? _errorLista;
  bool _cargando = true;

  final _montoController = TextEditingController();
  final _notaController = TextEditingController();
  DateTime? _fechaPago;
  ArchivoElegido? _archivo;
  bool _enviando = false;
  String? _errorFormulario;
  bool _enviado = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _montoController.dispose();
    _notaController.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _errorLista = null;
    });
    try {
      final lista = await widget.proofService.listarMisComprobantes(widget.token);
      if (!mounted) return;
      setState(() => _comprobantes = lista);
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorLista = err is ApiException ? err.message : 'No se pudieron cargar tus comprobantes.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _elegirArchivo(OrigenDelArchivo origen) async {
    final elegido = await widget.seleccionarArchivo(origen);
    if (elegido == null || !mounted) return;
    if (elegido.bytes.length > pesoMaximoDelComprobante) {
      setState(() => _errorFormulario = 'El archivo pesa más de 10 MB. Elige uno más ligero.');
      return;
    }
    setState(() {
      _archivo = elegido;
      _errorFormulario = null;
      _enviado = false;
    });
  }

  Future<void> _elegirFecha() async {
    final ahora = DateTime.now();
    final fecha = await showDatePicker(
      context: context,
      initialDate: _fechaPago ?? ahora,
      firstDate: DateTime(ahora.year - 1),
      lastDate: ahora,
    );
    if (fecha != null && mounted) setState(() => _fechaPago = fecha);
  }

  Future<void> _enviar() async {
    final monto = double.tryParse(_montoController.text.trim().replaceAll(',', '.'));
    if (monto == null || monto <= 0) {
      setState(() => _errorFormulario = 'Escribe el monto que pagaste.');
      return;
    }
    final archivo = _archivo;
    if (archivo == null) {
      setState(() => _errorFormulario = 'Adjunta la foto o el PDF de tu comprobante.');
      return;
    }
    setState(() {
      _enviando = true;
      _errorFormulario = null;
      _enviado = false;
    });
    try {
      final archivoId = await widget.proofService.subirArchivo(archivo.bytes, archivo.nombre, widget.token);
      await widget.proofService.enviarComprobante(
        monto: monto,
        archivoId: archivoId,
        fechaPago: _fechaPago,
        nota: _notaController.text,
        token: widget.token,
      );
      if (!mounted) return;
      setState(() {
        _montoController.clear();
        _notaController.clear();
        _fechaPago = null;
        _archivo = null;
        _enviado = true;
      });
      await _cargar();
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorFormulario = err is ApiException ? err.message : 'No se pudo enviar el comprobante.');
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  static String _pad(int n) => n.toString().padLeft(2, '0');

  String _fechaCorta(DateTime fecha) => '${fecha.year}-${_pad(fecha.month)}-${_pad(fecha.day)}';

  static String _kb(int bytes) =>
      bytes < 1024 * 1024 ? '${(bytes / 1024).round()} KB' : '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Comprobantes de pago')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.all(16),
          children: [
            _buildFormulario(),
            const SizedBox(height: 24),
            Text('Mis comprobantes', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ..._buildLista(),
          ],
        ),
      ),
    );
  }

  Widget _buildFormulario() {
    final archivo = _archivo;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('¿Ya pagaste?', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
              'Adjunta la captura o el PDF de tu transferencia. Tesorería lo revisa y, cuando confirma que el dinero llegó, '
              'lo aplica a tu cuenta.',
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('monto_comprobante_field'),
              controller: _montoController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Monto pagado', prefixText: '\$ '),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              key: const Key('fecha_pago_button'),
              onPressed: _elegirFecha,
              child: Text(_fechaPago == null ? 'Fecha del pago (opcional)' : _fechaCorta(_fechaPago!)),
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('nota_comprobante_field'),
              controller: _notaController,
              decoration: const InputDecoration(labelText: 'Nota (opcional)'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('elegir_foto_button'),
                    onPressed: _enviando ? null : () => _elegirArchivo(OrigenDelArchivo.foto),
                    icon: const Icon(Icons.photo),
                    label: const Text('Elegir foto'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('elegir_pdf_button'),
                    onPressed: _enviando ? null : () => _elegirArchivo(OrigenDelArchivo.pdf),
                    icon: const Icon(Icons.picture_as_pdf),
                    label: const Text('Elegir PDF'),
                  ),
                ),
              ],
            ),
            if (archivo != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Archivo: ${archivo.nombre} (${_kb(archivo.bytes.length)})',
                  key: const Key('archivo_elegido'),
                ),
              ),
            if (_errorFormulario != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _errorFormulario!,
                  key: const Key('error_comprobante'),
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            if (_enviado)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Comprobante enviado. Está en revisión.',
                  key: Key('comprobante_enviado'),
                  style: TextStyle(color: Colors.green),
                ),
              ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _enviando ? null : _enviar,
              child: Text(_enviando ? 'Enviando…' : 'Enviar comprobante'),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildLista() {
    if (_errorLista != null) return [Text(_errorLista!, style: const TextStyle(color: Colors.red))];
    final lista = _comprobantes;
    if (lista == null) return [if (_cargando) const Center(child: CircularProgressIndicator())];
    if (lista.isEmpty) return [const Text('Todavía no has enviado comprobantes.')];
    return lista.map(_buildComprobante).toList();
  }

  Widget _buildComprobante(PaymentProof c) {
    final (etiqueta, color, icono) = switch (c.estado) {
      'aceptado' => ('Aceptado', Colors.green, Icons.check_circle),
      'rechazado' => ('Rechazado', Colors.red, Icons.cancel),
      _ => ('En revisión', Colors.orange, Icons.hourglass_top),
    };
    return ListTile(
      key: Key('comprobante_${c.id}'),
      leading: Icon(icono, color: color),
      title: Text('\$${c.monto.toStringAsFixed(2)} · $etiqueta'),
      subtitle: Text(
        [
          'Enviado ${formatoFechaCorta(c.createdAt)}',
          if (c.fechaPago != null) 'pago del ${_fechaCorta(c.fechaPago!)}',
          if (c.estado == 'rechazado' && c.motivoRechazo != null) 'Motivo: ${c.motivoRechazo}',
        ].join(' · '),
      ),
      trailing: IconButton(
        key: Key('ver_comprobante_${c.id}'),
        icon: const Icon(Icons.attachment),
        tooltip: 'Ver archivo',
        onPressed: () => widget.abrirUrl(c.archivoUrl),
      ),
    );
  }
}
