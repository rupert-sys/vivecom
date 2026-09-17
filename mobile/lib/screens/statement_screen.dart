import 'package:flutter/material.dart';

import '../models/account_statement.dart';
import '../services/api_client.dart';
import '../services/statement_service.dart';
import '../utils/labels.dart';

class StatementScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final VoidCallback onLogout;

  const StatementScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.onLogout,
  });

  @override
  State<StatementScreen> createState() => _StatementScreenState();
}

class _StatementScreenState extends State<StatementScreen> {
  AccountStatement? _estado;
  String? _error;
  bool _cargando = true;

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
      setState(() => _error = err is ApiException ? err.message : 'No se pudo cargar el estado de cuenta.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  String _formatoMoneda(double valor) => '\$${valor.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Estado de cuenta'),
        actions: [
          IconButton(icon: const Icon(Icons.logout), tooltip: 'Cerrar sesión', onPressed: widget.onLogout),
        ],
      ),
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
    return _buildContenido(_estado!);
  }

  Widget _buildContenido(AccountStatement estado) {
    final deudaColor = estado.deudaTotal > 0 ? Colors.red.shade50 : Colors.green.shade50;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(estado.identificador, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 16),
        Card(
          color: deudaColor,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Deuda total: ${_formatoMoneda(estado.deudaTotal)}'),
                const SizedBox(height: 4),
                Text('Saldo a favor: ${_formatoMoneda(estado.saldoAFavor)}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        Text('Cargos', style: Theme.of(context).textTheme.titleMedium),
        if (estado.cargos.isEmpty) const Text('Todavía no hay cargos.'),
        ...estado.cargos.map(
          (c) => ListTile(
            title: Text('${c.periodo.year}-${c.periodo.month.toString().padLeft(2, '0')}'),
            subtitle: Text(etiquetasEstadoCargo[c.estado] ?? c.estado),
            trailing: Text(_formatoMoneda(c.montoBase + c.recargoAplicado)),
          ),
        ),
        const SizedBox(height: 24),
        Text('Pagos', style: Theme.of(context).textTheme.titleMedium),
        if (estado.pagos.isEmpty) const Text('Todavía no hay pagos registrados.'),
        ...estado.pagos.map(
          (p) => ListTile(
            title: Text(_formatoMoneda(p.monto)),
            subtitle: Text('${etiquetasEstadoPago[p.estado] ?? p.estado} · ${p.claveRastreo}'),
            trailing: Text(_formatoFecha(p.fechaDeteccion)),
          ),
        ),
      ],
    );
  }

  String _pad(int n) => n.toString().padLeft(2, '0');

  String _formatoFecha(DateTime fecha) {
    final local = fecha.toLocal();
    return '${local.year}-${_pad(local.month)}-${_pad(local.day)}';
  }
}
