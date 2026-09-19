import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../models/visitor_qr_validation.dart';
import '../services/api_client.dart';
import '../services/property_service.dart';
import '../services/visitor_qr_service.dart';
import '../widgets/provider_code_card.dart';

class QrScanScreen extends StatefulWidget {
  final String token;
  final VisitorQrService visitorQrService;
  final PropertyService propertyService;

  const QrScanScreen({
    super.key,
    required this.token,
    required this.visitorQrService,
    required this.propertyService,
  });

  @override
  State<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends State<QrScanScreen> {
  final MobileScannerController _controller = MobileScannerController();
  final _codigoController = TextEditingController();

  bool _validando = false;
  String? _error;
  VisitorQrValidation? _resultado;
  bool _escaneandoAhora = false; // evita mandar dos veces el mismo frame detectado

  @override
  void dispose() {
    _controller.dispose();
    _codigoController.dispose();
    super.dispose();
  }

  Future<void> _validar(String codigo) async {
    if (codigo.trim().isEmpty || _validando) return;
    setState(() {
      _validando = true;
      _error = null;
      _resultado = null;
    });
    try {
      final resultado = await widget.visitorQrService.validar(codigo.trim(), widget.token);
      if (!mounted) return;
      setState(() => _resultado = resultado);
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudo validar el código.');
    } finally {
      if (mounted) setState(() => _validando = false);
    }
  }

  Future<void> _onDetect(BarcodeCapture captura) async {
    if (_escaneandoAhora || captura.barcodes.isEmpty) return;
    final codigo = captura.barcodes.first.rawValue;
    if (codigo == null) return;
    _escaneandoAhora = true;
    await _validar(codigo);
    _escaneandoAhora = false;
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Escanear QR de visitante'),
        const SizedBox(height: 8),
        SizedBox(
          height: 260,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: MobileScanner(
              key: const Key('mobile_scanner'),
              controller: _controller,
              onDetect: _onDetect,
              errorBuilder: (context, error) =>
                  const ColoredBox(color: Colors.black12, child: Center(child: Text('Cámara no disponible en este dispositivo.'))),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextField(
                key: const Key('codigo_field'),
                controller: _codigoController,
                decoration: const InputDecoration(labelText: 'O ingresa el código manualmente'),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: _validando ? null : () => _validar(_codigoController.text),
              child: const Text('Validar'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_validando) const Center(child: CircularProgressIndicator()),
        if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
        if (_resultado != null) _buildResultado(_resultado!),
        const SizedBox(height: 24),
        ProviderCodeCard(
          token: widget.token,
          visitorQrService: widget.visitorQrService,
          propertyService: widget.propertyService,
        ),
      ],
    );
  }

  Widget _buildResultado(VisitorQrValidation resultado) {
    if (resultado.valido) {
      return Card(
        color: Colors.green.withValues(alpha: 0.1),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.green),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Acceso autorizado.', style: TextStyle(fontWeight: FontWeight.bold)),
                    if (resultado.tipo == 'proveedor')
                      Text('Proveedor${resultado.descripcion != null ? ': ${resultado.descripcion}' : ''}'),
                    Text(
                      resultado.vivienda != null ? 'Va a: ${resultado.vivienda}' : 'Servicio al condominio en general',
                      key: const Key('destino_qr'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }
    final motivo = switch (resultado.motivo) {
      'ya_usado' => 'Este código ya fue usado.',
      'no_existe' => 'Este código no existe.',
      _ => 'Código inválido.',
    };
    return Card(
      color: Colors.red.withValues(alpha: 0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(children: [const Icon(Icons.cancel, color: Colors.red), const SizedBox(width: 8), Text(motivo)]),
      ),
    );
  }
}
