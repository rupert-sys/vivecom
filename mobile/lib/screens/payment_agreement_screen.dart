import 'package:flutter/material.dart';

import '../models/payment_agreement.dart';
import '../services/api_client.dart';
import '../services/payment_agreement_service.dart';
import '../utils/dates.dart';
import 'payment_proof_screen.dart'
    show ArchivoElegido, OrigenDelArchivo, SeleccionarArchivo, pesoMaximoDelComprobante, seleccionarArchivoReal;

const int minimoCausa = 20;

// Acuerdo de pago (prórroga de cuotas, reglamento Art. 1 VIII y 9 VII): "no puedo pagar a tiempo por una causa
// justificada". Se solicita por escrito, el comité decide y, mientras se cumple, no cuentas como moroso.
class PaymentAgreementScreen extends StatefulWidget {
  final String token;
  final PaymentAgreementService agreementService;
  final SeleccionarArchivo seleccionarArchivo;

  const PaymentAgreementScreen({
    super.key,
    required this.token,
    required this.agreementService,
    this.seleccionarArchivo = seleccionarArchivoReal,
  });

  @override
  State<PaymentAgreementScreen> createState() => _PaymentAgreementScreenState();
}

class _PaymentAgreementScreenState extends State<PaymentAgreementScreen> {
  List<PaymentAgreement>? _acuerdos;
  String? _errorLista;
  bool _cargando = true;

  final _causaController = TextEditingController();
  int _numeroDePagos = 1;
  DateTime? _primerPago;
  ArchivoElegido? _documento;
  bool _enviando = false;
  String? _errorFormulario;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _causaController.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _errorLista = null;
    });
    try {
      final lista = await widget.agreementService.listarMisAcuerdos(widget.token);
      if (!mounted) return;
      setState(() => _acuerdos = lista);
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorLista = err is ApiException ? err.message : 'No se pudieron cargar tus acuerdos.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _elegirFecha() async {
    final ahora = DateTime.now();
    final fecha = await showDatePicker(
      context: context,
      initialDate: _primerPago ?? ahora.add(const Duration(days: 7)),
      firstDate: ahora.add(const Duration(days: 1)),
      lastDate: ahora.add(const Duration(days: 200)),
    );
    if (fecha != null && mounted) setState(() => _primerPago = fecha);
  }

  Future<void> _elegirDocumento(OrigenDelArchivo origen) async {
    final elegido = await widget.seleccionarArchivo(origen);
    if (elegido == null || !mounted) return;
    if (elegido.bytes.length > pesoMaximoDelComprobante) {
      setState(() => _errorFormulario = 'El archivo pesa más de 10 MB. Elige uno más ligero.');
      return;
    }
    setState(() {
      _documento = elegido;
      _errorFormulario = null;
    });
  }

  Future<void> _enviar() async {
    if (_causaController.text.trim().length < minimoCausa) {
      setState(() => _errorFormulario = 'Cuéntale al comité la causa con al menos $minimoCausa caracteres.');
      return;
    }
    final primerPago = _primerPago;
    if (primerPago == null) {
      setState(() => _errorFormulario = 'Elige la fecha de tu primer pago.');
      return;
    }
    setState(() {
      _enviando = true;
      _errorFormulario = null;
    });
    try {
      final documento = _documento;
      final archivoId = documento == null
          ? null
          : await widget.agreementService.subirDocumento(documento.bytes, documento.nombre, widget.token);
      await widget.agreementService.solicitar(
        causa: _causaController.text,
        numeroDePagos: _numeroDePagos,
        primerPago: primerPago,
        archivoId: archivoId,
        token: widget.token,
      );
      if (!mounted) return;
      setState(() {
        _causaController.clear();
        _primerPago = null;
        _documento = null;
        _numeroDePagos = 1;
      });
      await _cargar();
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorFormulario = err is ApiException ? err.message : 'No se pudo enviar tu solicitud.');
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  Future<void> _retirar(PaymentAgreement acuerdo) async {
    try {
      await widget.agreementService.retirarSolicitud(acuerdo.id, widget.token);
      await _cargar();
    } catch (err) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(err is ApiException ? err.message : 'No se pudo retirar la solicitud.')));
    }
  }

  static String _dinero(double valor) => '\$${valor.toStringAsFixed(2)}';
  static String _dia(DateTime f) => formatoFechaCorta(f);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Acuerdo de pago')),
      body: RefreshIndicator(onRefresh: _cargar, child: _buildCuerpo()),
    );
  }

  Widget _buildCuerpo() {
    if (_cargando && _acuerdos == null) return const Center(child: CircularProgressIndicator());
    if (_errorLista != null && _acuerdos == null) {
      return ListView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_errorLista!, style: const TextStyle(color: Colors.red)),
          ),
        ],
      );
    }
    final acuerdos = _acuerdos ?? [];
    final abierto = acuerdos.where((a) => a.abierto).firstOrNull;
    final anteriores = acuerdos.where((a) => !a.abierto).toList();
    return ListView(
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.all(16),
      children: [
        if (abierto != null) _buildAbierto(abierto) else _buildFormulario(),
        if (anteriores.isNotEmpty) ...[
          const SizedBox(height: 24),
          Text('Anteriores', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...anteriores.map(_buildAnterior),
        ],
      ],
    );
  }

  Widget _buildFormulario() {
    final documento = _documento;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('¿No puedes pagar a tiempo?', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
              'Si tienes una causa justificada, pide un acuerdo de pago por escrito. El comité lo revisa y, si lo aprueba, '
              'mientras cumplas no cuentas como moroso: conservas tu voto y las áreas comunes.',
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('causa_field'),
              controller: _causaController,
              maxLength: 1000,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Causa justificada'),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<int>(
              key: const Key('numero_de_pagos'),
              initialValue: _numeroDePagos,
              decoration: const InputDecoration(labelText: 'En cuántos pagos mensuales'),
              items: [
                const DropdownMenuItem(value: 1, child: Text('1 pago (todo en una fecha)')),
                ...[2, 3, 4, 5, 6].map((n) => DropdownMenuItem(value: n, child: Text('$n pagos'))),
              ],
              onChanged: (n) => setState(() => _numeroDePagos = n ?? 1),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              key: const Key('primer_pago_button'),
              onPressed: _elegirFecha,
              child: Text(_primerPago == null ? 'Fecha del primer pago' : _dia(_primerPago!)),
            ),
            const SizedBox(height: 12),
            const Text('Escrito o documento de respaldo (opcional)'),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('elegir_foto_acuerdo'),
                    onPressed: _enviando ? null : () => _elegirDocumento(OrigenDelArchivo.foto),
                    icon: const Icon(Icons.photo),
                    label: const Text('Foto'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('elegir_pdf_acuerdo'),
                    onPressed: _enviando ? null : () => _elegirDocumento(OrigenDelArchivo.pdf),
                    icon: const Icon(Icons.picture_as_pdf),
                    label: const Text('PDF'),
                  ),
                ),
              ],
            ),
            if (documento != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text('Adjunto: ${documento.nombre}', key: const Key('documento_elegido')),
              ),
            if (_errorFormulario != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _errorFormulario!,
                  key: const Key('error_acuerdo'),
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _enviando ? null : _enviar,
              child: Text(_enviando ? 'Enviando…' : 'Enviar solicitud'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAbierto(PaymentAgreement a) {
    if (a.estado == 'solicitado') {
      return Card(
        key: const Key('acuerdo_solicitado'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Tu solicitud está en revisión', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(
                'Propones ${a.propuestaPagos == 1 ? 'pagar todo' : '${a.propuestaPagos} pagos mensuales'} desde el ${_dia(a.propuestaPrimerPago)}.',
              ),
              const SizedBox(height: 8),
              const Text(
                'Mientras el comité decide, tu adeudo sigue corriendo como siempre. Te avisamos aquí cuando responda.',
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                key: const Key('retirar_solicitud'),
                onPressed: () => _retirar(a),
                child: const Text('Retirar solicitud'),
              ),
            ],
          ),
        ),
      );
    }
    final deuda = a.deudaInicial ?? 0;
    final abonado = a.abonado ?? 0;
    return Card(
      key: const Key('acuerdo_vigente'),
      color: Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Tienes un acuerdo de pago vigente', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Mientras cumplas el calendario no cuentas como moroso: conservas tu voto y las áreas comunes.'),
            if (a.congelaRecargo == true)
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('Tu recargo está congelado mientras cumplas.', key: Key('recargo_congelado')),
              ),
            const SizedBox(height: 12),
            LinearProgressIndicator(value: deuda <= 0 ? 0 : (abonado / deuda).clamp(0.0, 1.0)),
            const SizedBox(height: 4),
            Text('Llevas ${_dinero(abonado)} de ${_dinero(deuda)}', key: const Key('avance_acuerdo')),
            if (a.proximoPago != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Próximo pago: ${_dinero(a.proximoPago!.monto)} el ${_dia(a.proximoPago!.fecha)}',
                  key: const Key('proximo_pago'),
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            const SizedBox(height: 12),
            const Text('Calendario'),
            ...a.calendario.map((p) => Text('• ${_dia(p.fecha)}: ${_dinero(p.monto)}')),
            const SizedBox(height: 8),
            const Text(
              'Las cuotas de cada mes nuevas se pagan normal, además de tu calendario.',
              style: TextStyle(fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnterior(PaymentAgreement a) {
    final (etiqueta, color) = switch (a.estado) {
      'cumplido' => ('Cumplido', Colors.green),
      'incumplido' => ('Incumplido', Colors.red),
      'rechazado' => ('Rechazado', Colors.red),
      _ => ('Cancelado', Colors.grey),
    };
    return ListTile(
      key: Key('acuerdo_${a.id}'),
      leading: Icon(Icons.history, color: color),
      title: Text(etiqueta),
      subtitle: Text(
        [
          'Solicitado ${_dia(a.createdAt)}',
          if (a.estado == 'rechazado' && a.motivoRechazo != null) 'Motivo: ${a.motivoRechazo}',
          if (a.estado == 'incumplido') 'Vuelves a estar en mora por lo pendiente',
        ].join(' · '),
      ),
    );
  }
}
