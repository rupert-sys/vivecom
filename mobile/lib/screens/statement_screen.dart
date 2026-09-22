import 'package:flutter/material.dart';

import '../models/account_statement.dart';
import '../services/tenant_service.dart';
import '../services/api_client.dart';
import '../services/statement_service.dart';
import '../utils/dates.dart';
import '../utils/labels.dart';
import '../widgets/instalar_app.dart';

class StatementScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final TenantService tenantService;
  final VoidCallback onLogout;
  // Bajar el APK (Android) o añadir la app a la pantalla de inicio (iPhone): solo en la versión web. Va aquí y no solo
  // en el inicio de sesión porque la sesión se guarda: quien ya entró no vuelve a ver esa pantalla.
  final Widget instalarApp;

  const StatementScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.tenantService,
    required this.onLogout,
    this.instalarApp = const InstalarApp(),
  });

  @override
  State<StatementScreen> createState() => _StatementScreenState();
}

class _StatementScreenState extends State<StatementScreen> {
  AccountStatement? _estado;
  String? _error;
  bool _cargando = true;
  // Nombre del condominio: es solo contexto ("¿de cuál condominio es esta cuenta?"), así que si falla no bloquea
  // ni se le avisa al residente — el estado de cuenta se ve completo de todos modos.
  String? _nombreCondominio;

  @override
  void initState() {
    super.initState();
    _cargar();
    _cargarNombreCondominio();
  }

  Future<void> _cargarNombreCondominio() async {
    try {
      final config = await widget.tenantService.obtenerConfiguracion(widget.token);
      if (mounted) setState(() => _nombreCondominio = config.nombre);
    } catch (_) {
      // Sin indicador de error: es solo contexto, ver el comentario del campo.
    }
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
        actions: [IconButton(icon: const Icon(Icons.logout), tooltip: 'Cerrar sesión', onPressed: widget.onLogout)],
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

  // Cuotas vencidas: se dice de frente qué implica según el reglamento del condominio.
  Widget _buildAvisoDeMora(AccountStatement estado) {
    return Card(
      key: const Key('aviso_mora'),
      color: Colors.orange.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Tu vivienda tiene cuotas vencidas', style: TextStyle(fontWeight: FontWeight.bold)),
            ...estado.restriccionesPorMora.map(
              (r) => Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $r')),
            ),
            const SizedBox(height: 4),
            const Text('Se levantan en cuanto te pongas al corriente.'),
            const Text('Si tienes una causa justificada, puedes pedir un acuerdo de pago en la pestaña Pago.'),
          ],
        ),
      ),
    );
  }

  // Con un acuerdo de pago vigente lo cubierto no cuenta como mora: se dice de frente.
  Widget _buildAvisoDeAcuerdo() {
    return Card(
      key: const Key('aviso_acuerdo'),
      color: Colors.blue.shade50,
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          'Tienes un acuerdo de pago vigente. Mientras cumplas el calendario no cuentas como moroso. '
          'Lo ves en la pestaña Pago.',
        ),
      ),
    );
  }

  Widget _buildContenido(AccountStatement estado) {
    final deudaColor = estado.deudaTotal > 0 ? Colors.red.shade50 : Colors.green.shade50;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (_nombreCondominio != null)
          Text(
            _nombreCondominio!,
            key: const Key('nombre_condominio'),
            style: Theme.of(context).textTheme.labelLarge
                ?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
          ),
        Text(estado.identificador, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 16),
        widget.instalarApp,
        if (estado.enMora) ...[_buildAvisoDeMora(estado), const SizedBox(height: 16)],
        if (estado.enAcuerdo) ...[_buildAvisoDeAcuerdo(), const SizedBox(height: 16)],
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
            trailing: Text(formatoFechaCorta(p.fechaDeteccion)),
          ),
        ),
      ],
    );
  }
}
