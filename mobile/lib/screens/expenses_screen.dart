import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/expense.dart';
import '../services/api_client.dart';
import '../services/expense_service.dart';
import '../utils/dates.dart';

// Inyectable para que las pruebas de widget no invoquen url_launcher de
// verdad (mismo patrón que CompartirPdf en payment_history_screen.dart).
typedef AbrirUrl = Future<void> Function(String url);

Future<void> abrirUrlReal(String url) async {
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
}

class ExpensesScreen extends StatefulWidget {
  final String token;
  final ExpenseService expenseService;
  final AbrirUrl abrirUrl;

  const ExpensesScreen({
    super.key,
    required this.token,
    required this.expenseService,
    this.abrirUrl = abrirUrlReal,
  });

  @override
  State<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends State<ExpensesScreen> {
  List<Expense>? _gastos;
  ExpenseSummary? _resumen;
  String? _error;
  bool _cargando = true;

  DateTime? _desde;
  DateTime? _hasta;
  final _categoriaController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _categoriaController.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final gastos = await widget.expenseService.listarGastos(
        widget.token,
        desde: _desde,
        hasta: _hasta,
        categoria: _categoriaController.text,
      );
      if (!mounted) return;
      setState(() => _gastos = gastos);
      // El resumen es un complemento: si falla, la lista de gastos sigue siendo útil.
      try {
        final resumen = await widget.expenseService.obtenerResumen(widget.token, desde: _desde, hasta: _hasta);
        if (mounted) setState(() => _resumen = resumen);
      } catch (_) {
        if (mounted) setState(() => _resumen = null);
      }
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudieron cargar los gastos.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _limpiarFiltros() async {
    setState(() {
      _desde = null;
      _hasta = null;
      _categoriaController.clear();
    });
    await _cargar();
  }

  Future<void> _elegirFecha({required bool esDesde}) async {
    final ahora = DateTime.now();
    final elegida = await showDatePicker(
      context: context,
      initialDate: (esDesde ? _desde : _hasta) ?? ahora,
      firstDate: DateTime(ahora.year - 5),
      lastDate: ahora,
    );
    if (elegida == null) return;
    setState(() {
      if (esDesde) {
        _desde = elegida;
      } else {
        _hasta = elegida;
      }
    });
    await _cargar();
  }

  String _formatoMoneda(double valor) => '\$${valor.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Gastos del condominio')),
      body: RefreshIndicator(onRefresh: _cargar, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildFiltros(),
        const SizedBox(height: 16),
        if (_resumen != null) ...[_buildResumen(_resumen!), const SizedBox(height: 16)],
        if (_cargando && _gastos == null)
          const Center(child: CircularProgressIndicator())
        else if (_error != null)
          Text(_error!, style: const TextStyle(color: Colors.red))
        else
          _buildLista(_gastos!),
      ],
    );
  }

  Widget _buildFiltros() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Filtrar por periodo'),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _elegirFecha(esDesde: true),
                    child: Text(_desde == null ? 'Desde' : formatoFechaCorta(_desde!)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _elegirFecha(esDesde: false),
                    child: Text(_hasta == null ? 'Hasta' : formatoFechaCorta(_hasta!)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('categoria_field'),
              controller: _categoriaController,
              decoration: const InputDecoration(labelText: 'Categoría'),
              onSubmitted: (_) => _cargar(),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                ElevatedButton(onPressed: _cargar, child: const Text('Filtrar')),
                const SizedBox(width: 8),
                TextButton(onPressed: _limpiarFiltros, child: const Text('Limpiar filtros')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // Cuánto entró, cuánto se gastó y cómo queda el condominio (a favor o en contra).
  Widget _buildResumen(ExpenseSummary resumen) {
    final aFavor = resumen.saldo >= 0;
    return Card(
      key: const Key('resumen_financiero'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Resumen del condominio', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            _filaResumen('Ingresos (cuotas cobradas)', resumen.ingresos),
            _filaResumen('Gastos', resumen.gastos),
            const Divider(),
            _filaResumen(aFavor ? 'Saldo a favor' : 'Saldo en contra', resumen.saldo.abs(),
                color: aFavor ? Colors.green.shade800 : Colors.red, negrita: true),
            _filaResumen('Cuotas por cobrar', resumen.porCobrar),
            if (resumen.gastosPorCategoria.isNotEmpty) ...[
              const SizedBox(height: 8),
              const Text('Gastos por categoría'),
              ...resumen.gastosPorCategoria.map((c) => _filaResumen('${c.concepto} (${c.cantidad})', c.total)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _filaResumen(String etiqueta, double valor, {Color? color, bool negrita = false}) {
    final estilo = TextStyle(color: color, fontWeight: negrita ? FontWeight.bold : null);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [Text(etiqueta, style: estilo), Text(_formatoMoneda(valor), style: estilo)],
      ),
    );
  }

  Widget _buildLista(List<Expense> gastos) {
    if (gastos.isEmpty) {
      return const Text('No hay gastos registrados en este periodo.');
    }
    final total = gastos.fold<double>(0, (suma, gasto) => suma + gasto.monto);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Total: ${_formatoMoneda(total)}', style: Theme.of(context).textTheme.titleMedium),
        const Divider(),
        ...gastos.map(
          (gasto) => ListTile(
            title: Text(gasto.categoria),
            subtitle: Text(formatoFechaCorta(gasto.fecha)),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(_formatoMoneda(gasto.monto)),
                IconButton(
                  key: Key('ver_comprobante_${gasto.id}'),
                  icon: const Icon(Icons.receipt),
                  tooltip: 'Ver comprobante',
                  onPressed: () => widget.abrirUrl(gasto.comprobanteUrl),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
