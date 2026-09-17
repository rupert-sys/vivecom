import 'package:flutter/material.dart';

import '../models/account_statement.dart';
import '../models/fee.dart';
import '../models/property_detail.dart';
import '../models/tenant_clabe.dart';
import '../services/api_client.dart';
import '../services/clabe_service.dart';
import '../services/fee_service.dart';
import '../services/property_service.dart';
import '../services/statement_service.dart';
import '../utils/labels.dart';

class PaymentScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final PropertyService propertyService;
  final FeeService feeService;
  final ClabeService clabeService;

  const PaymentScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.propertyService,
    required this.feeService,
    required this.clabeService,
  });

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  AccountStatement? _estado;
  PropertyDetail? _propiedad;
  Fee? _cuotaVigente;
  TenantClabe? _clabe;
  String? _error;
  bool _cargando = true;

  int _mesesSeleccionados = 1;

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
      final resultados = await Future.wait([
        widget.statementService.obtenerEstadoDeCuenta(widget.propertyId, widget.token),
        widget.propertyService.obtenerPropiedad(widget.propertyId, widget.token),
        widget.feeService.obtenerCuotaVigente(widget.token),
        widget.clabeService.obtenerClabe(widget.token),
      ]);
      if (!mounted) return;
      setState(() {
        _estado = resultados[0] as AccountStatement;
        _propiedad = resultados[1] as PropertyDetail;
        _cuotaVigente = resultados[2] as Fee?;
        _clabe = resultados[3] as TenantClabe;
      });
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudo cargar la información de pago.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  String _formatoMoneda(double valor) => '\$${valor.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pago')),
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
    return _buildContenido();
  }

  Widget _buildContenido() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Estado del pago más reciente', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _buildUltimoPago(),
        const SizedBox(height: 32),
        Text('Pago anticipado', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _buildPagoAnticipado(),
      ],
    );
  }

  Widget _buildUltimoPago() {
    final pagos = _estado!.pagos;
    if (pagos.isEmpty) {
      return const Card(
        child: Padding(padding: EdgeInsets.all(16), child: Text('Todavía no hay pagos registrados.')),
      );
    }
    // El backend regresa los pagos ordenados por fecha_deteccion DESC (ver
    // statement_service.py), así que el primero es el más reciente.
    final ultimo = pagos.first;
    final colorEstado = switch (ultimo.estado) {
      'confirmado' => Colors.green.shade50,
      'rechazado' => Colors.red.shade50,
      _ => Colors.amber.shade50,
    };
    return Card(
      color: colorEstado,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_formatoMoneda(ultimo.monto), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(etiquetasEstadoPago[ultimo.estado] ?? ultimo.estado, key: const Key('estado_ultimo_pago')),
            Text('Referencia: ${ultimo.claveRastreo}'),
          ],
        ),
      ),
    );
  }

  Widget _buildPagoAnticipado() {
    final cuota = _cuotaVigente;
    if (cuota == null) {
      return const Card(
        child: Padding(padding: EdgeInsets.all(16), child: Text('No hay una cuota configurada todavía.')),
      );
    }
    // F1-08: el pago anticipado por número de meses solo se detecta
    // automáticamente para cuotas MENSUALES — con periodicidad bimestral el
    // excedente cae al camino genérico de saldo a favor (F1-09), no a meses
    // exactos, así que mostrar aquí un calculador de "N meses" sería engañoso.
    if (cuota.periodicidad != 'mensual') {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'El pago anticipado por número de meses no está disponible con la periodicidad de cuota actual (bimestral). '
            'Cualquier excedente que transfieras se aplicará como saldo a favor.',
          ),
        ),
      );
    }

    final deudaTotal = _estado!.deudaTotal;
    final total = deudaTotal + (_mesesSeleccionados * cuota.monto);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('¿Cuántos meses quieres adelantar?'),
            const SizedBox(height: 8),
            DropdownButton<int>(
              key: const Key('meses_dropdown'),
              value: _mesesSeleccionados,
              items: List.generate(12, (i) => i + 1)
                  .map((mes) => DropdownMenuItem(value: mes, child: Text('$mes ${mes == 1 ? 'mes' : 'meses'}')))
                  .toList(),
              onChanged: (valor) {
                if (valor != null) setState(() => _mesesSeleccionados = valor);
              },
            ),
            const SizedBox(height: 16),
            if (deudaTotal > 0) Text('Deuda actual: ${_formatoMoneda(deudaTotal)}'),
            Text('$_mesesSeleccionados × ${_formatoMoneda(cuota.monto)} de cuota mensual'),
            const Divider(height: 24),
            Text(
              'Transfiere ${_formatoMoneda(total)}',
              key: const Key('total_a_transferir'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text('CLABE: ${_clabe!.clabeDestino}'),
            Text('Referencia: ${_propiedad!.referenciaPago}'),
          ],
        ),
      ),
    );
  }
}
