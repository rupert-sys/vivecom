import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:printing/printing.dart';

import '../models/account_statement.dart';
import '../services/api_client.dart';
import '../services/receipt_service.dart';
import '../services/statement_service.dart';
import '../utils/dates.dart';
import '../utils/labels.dart';

// Inyectable para que las pruebas de widget no toquen el canal de plataforma
// real del paquete printing (que abre la hoja de compartir del sistema).
typedef CompartirPdf = Future<void> Function(Uint8List bytes, String filename);

Future<void> compartirPdfReal(Uint8List bytes, String filename) {
  return Printing.sharePdf(bytes: bytes, filename: filename);
}

class PaymentHistoryScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final ReceiptService receiptService;
  final CompartirPdf compartirPdf;

  const PaymentHistoryScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.receiptService,
    this.compartirPdf = compartirPdfReal,
  });

  @override
  State<PaymentHistoryScreen> createState() => _PaymentHistoryScreenState();
}

class _PaymentHistoryScreenState extends State<PaymentHistoryScreen> {
  AccountStatement? _estado;
  String? _error;
  bool _cargando = true;
  String? _descargandoReciboDe;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final estado = await widget.statementService.obtenerEstadoDeCuenta(widget.propertyId, widget.token);
      if (!mounted) return;
      setState(() => _estado = estado);
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudo cargar el historial de pagos.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _verRecibo(PaymentSummary pago) async {
    setState(() => _descargandoReciboDe = pago.id);
    try {
      final bytes = await widget.receiptService.descargarRecibo(pago.id, widget.token);
      await widget.compartirPdf(bytes, 'recibo-${pago.claveRastreo}.pdf');
    } catch (err) {
      if (!mounted) return;
      final mensaje = err is ApiException ? err.message : 'No se pudo descargar el recibo.';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(mensaje)));
    } finally {
      if (mounted) setState(() => _descargandoReciboDe = null);
    }
  }

  String _formatoMoneda(double valor) => '\$${valor.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Historial de pagos')),
      body: RefreshIndicator(onRefresh: _cargar, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_cargando && _estado == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _estado == null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        ],
      );
    }
    final pagos = _estado!.pagos;
    if (pagos.isEmpty) {
      return ListView(
        children: const [
          Padding(padding: EdgeInsets.all(24), child: Text('Todavía no hay pagos registrados.')),
        ],
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: pagos.length,
      separatorBuilder: (_, _) => const Divider(),
      itemBuilder: (context, indice) => _buildPago(pagos[indice]),
    );
  }

  Widget _buildPago(PaymentSummary pago) {
    final descargando = _descargandoReciboDe == pago.id;
    return ListTile(
      title: Text(_formatoMoneda(pago.monto)),
      subtitle: Text(
        '${etiquetasEstadoPago[pago.estado] ?? pago.estado} · ${formatoFechaCorta(pago.fechaDeteccion)} · ${pago.claveRastreo}',
      ),
      trailing: pago.estado != 'confirmado'
          ? null
          : descargando
          ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2))
          : IconButton(
              key: Key('ver_recibo_${pago.id}'),
              icon: const Icon(Icons.receipt_long),
              tooltip: 'Ver recibo',
              onPressed: () => _verRecibo(pago),
            ),
    );
  }
}
