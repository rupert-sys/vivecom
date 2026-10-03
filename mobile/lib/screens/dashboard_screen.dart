import 'package:flutter/material.dart';

import '../models/account_statement.dart';
import '../models/cash_balance.dart';
import '../models/expense.dart';
import '../services/api_client.dart';
import '../services/cash_movement_service.dart';
import '../services/expense_service.dart';
import '../services/statement_service.dart';

// Visibilidad financiera del condominio en un solo lugar (F0-12): el estado de cuenta propio, el
// resumen de ingresos/egresos del condominio y el saldo de caja chica y grande — antes repartidos
// en las pestañas de Estado de cuenta y Gastos, y la caja no se mostraba en absoluto.
class DashboardScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final ExpenseService expenseService;
  final CashMovementService cashMovementService;

  const DashboardScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.expenseService,
    required this.cashMovementService,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  AccountStatement? _estado;
  ExpenseSummary? _resumen;
  CashBalance? _caja;
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
      if (mounted) setState(() => _estado = estado);
    } catch (err) {
      if (mounted) setState(() => _error = err is ApiException ? err.message : 'No se pudo cargar tu estado de cuenta.');
    }
    try {
      final resumen = await widget.expenseService.obtenerResumen(widget.token);
      if (mounted) setState(() => _resumen = resumen);
    } catch (_) {
      if (mounted) setState(() => _resumen = null);
    }
    try {
      final caja = await widget.cashMovementService.obtenerBalance(widget.token);
      if (mounted) setState(() => _caja = caja);
    } catch (_) {
      if (mounted) setState(() => _caja = null);
    }
    if (mounted) setState(() => _cargando = false);
  }

  String _formatoMoneda(double valor) => '\$${valor.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Dashboard')),
      body: RefreshIndicator(onRefresh: _cargar, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_cargando && _estado == null && _error == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 16), child: Text(_error!, style: const TextStyle(color: Colors.red))),
        if (_estado != null) ...[_buildEstadoDeCuenta(_estado!), const SizedBox(height: 16)],
        if (_resumen != null) ...[_buildResumenCondominio(_resumen!), const SizedBox(height: 16)],
        if (_caja != null) _buildCaja(_caja!),
      ],
    );
  }

  Widget _buildEstadoDeCuenta(AccountStatement estado) {
    return Card(
      key: const Key('dashboard_estado_de_cuenta'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Tu vivienda', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            _fila('Saldo a favor', estado.saldoAFavor, color: Colors.green.shade800),
            _fila('Adeudo', estado.deudaTotal, color: estado.deudaTotal > 0 ? Colors.red : null),
          ],
        ),
      ),
    );
  }

  Widget _buildResumenCondominio(ExpenseSummary resumen) {
    final aFavor = resumen.saldo >= 0;
    return Card(
      key: const Key('dashboard_resumen_condominio'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('El condominio', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            _fila('Ingresos', resumen.ingresos),
            _fila('Egresos', resumen.gastos),
            const Divider(),
            _fila(aFavor ? 'Saldo a favor' : 'Saldo en contra', resumen.saldo.abs(),
                color: aFavor ? Colors.green.shade800 : Colors.red, negrita: true),
          ],
        ),
      ),
    );
  }

  Widget _buildCaja(CashBalance caja) {
    return Card(
      key: const Key('dashboard_caja'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Caja chica y grande', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            _fila('Caja chica', caja.chica),
            _fila('Caja grande', caja.grande),
          ],
        ),
      ),
    );
  }

  Widget _fila(String etiqueta, double valor, {Color? color, bool negrita = false}) {
    final estilo = TextStyle(color: color, fontWeight: negrita ? FontWeight.bold : null);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [Text(etiqueta, style: estilo), Text(_formatoMoneda(valor), style: estilo)],
      ),
    );
  }
}
