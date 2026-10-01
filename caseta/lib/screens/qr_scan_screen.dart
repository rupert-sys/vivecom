import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/visitor_qr_validation.dart';
import '../services/api_client.dart';
import '../services/property_service.dart';
import '../services/visitor_qr_service.dart';
import '../widgets/provider_code_card.dart';

// Función inyectable para poder probar la pantalla sin depender del canal de plataforma real de url_launcher.
typedef LlamarTelefono = Future<void> Function(String telefono);

Future<void> llamarConElMarcadorDelSistema(String telefono) async {
  await launchUrl(Uri(scheme: 'tel', path: telefono));
}

class QrScanScreen extends StatefulWidget {
  final String token;
  final VisitorQrService visitorQrService;
  final PropertyService propertyService;
  final LlamarTelefono llamar;

  const QrScanScreen({
    super.key,
    required this.token,
    required this.visitorQrService,
    required this.propertyService,
    this.llamar = llamarConElMarcadorDelSistema,
  });

  @override
  State<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends State<QrScanScreen> {
  final MobileScannerController _controller = MobileScannerController();
  final _codigoController = TextEditingController();

  bool _validando = false;
  String? _error;
  bool _sinConexion = false;
  VisitorQrValidation? _resultado;
  VisitorQrOfflineInfo? _infoOffline;
  // El código real a validar cuando el guardia confirme — puede venir del payload leído, o ser el texto
  // pelón si no se pudo leer nada (código de proveedor, o un QR viejo sin el payload nuevo).
  String? _codigoPendiente;
  bool _escaneandoAhora = false; // evita mandar dos veces el mismo frame detectado

  @override
  void dispose() {
    _controller.dispose();
    _codigoController.dispose();
    super.dispose();
  }

  // Paso 1: leer el código — nunca toca la red. Muestra de inmediato lo que el propio código ya trae
  // escrito (nombre del visitante, casa, a quién llamar), para que el guardia lo corrobore con la persona
  // que tiene enfrente ANTES de autorizar el acceso. Encontrado en pruebas reales: validar y consumir el
  // código de inmediato al escanearlo no le daba tiempo al guardia de verificar nada.
  void _leer(String codigoEscaneado) {
    final texto = codigoEscaneado.trim();
    if (texto.isEmpty) return;
    final info = VisitorQrOfflineInfo.intentarLeer(texto);
    setState(() {
      _infoOffline = info;
      _codigoPendiente = info?.codigo ?? texto;
      _resultado = null;
      _error = null;
      _sinConexion = false;
    });
  }

  // Paso 2: el guardia ya corroboró con el visitante — aquí sí se consulta al servidor y, si es válido, se
  // consume de una vez (un mismo código nunca autoriza dos entradas).
  Future<void> _confirmarAcceso() async {
    final codigo = _codigoPendiente;
    if (codigo == null || _validando) return;
    setState(() {
      _validando = true;
      _error = null;
      _sinConexion = false;
    });
    try {
      final resultado = await widget.visitorQrService.validar(codigo, widget.token);
      if (!mounted) return;
      setState(() => _resultado = resultado);
    } on ApiException catch (err) {
      if (!mounted) return;
      setState(() => _error = err.message);
    } catch (_) {
      // Sin ApiException: no hubo respuesta del servidor (sin conexión, timeout). Si el QR traía datos
      // legibles, el guardia los sigue viendo — solo no se pudo confirmar si el código ya se usó.
      if (!mounted) return;
      setState(() => _sinConexion = true);
    } finally {
      if (mounted) setState(() => _validando = false);
    }
  }

  Future<void> _onDetect(BarcodeCapture captura) async {
    if (_escaneandoAhora || captura.barcodes.isEmpty) return;
    final codigo = captura.barcodes.first.rawValue;
    if (codigo == null) return;
    _escaneandoAhora = true;
    _leer(codigo);
    _escaneandoAhora = false;
  }

  @override
  Widget build(BuildContext context) {
    final telefono = _infoOffline?.telefonoResidente ?? _resultado?.telefonoResidente;
    final hayPendiente = _codigoPendiente != null && _resultado == null;
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
              onPressed: () => _leer(_codigoController.text),
              child: const Text('Leer código'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_infoOffline != null && _resultado == null) _buildInfoOffline(_infoOffline!),
        if (telefono != null && _resultado?.valido != false)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: OutlinedButton.icon(
              key: const Key('llamar_residente'),
              onPressed: () => widget.llamar(telefono),
              icon: const Icon(Icons.call),
              label: Text('Llamar a $telefono'),
            ),
          ),
        if (hayPendiente)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: ElevatedButton.icon(
              key: const Key('confirmar_acceso'),
              onPressed: _validando ? null : _confirmarAcceso,
              icon: const Icon(Icons.check),
              label: Text(_validando ? 'Confirmando…' : 'Confirmar acceso'),
            ),
          ),
        if (_sinConexion)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text(
              'Sin conexión — no se pudo confirmar si el código ya se usó. Verifica manualmente si es necesario.',
              key: Key('sin_conexion_qr'),
              style: TextStyle(color: Colors.orange),
            ),
          ),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
        if (_resultado != null) Padding(padding: const EdgeInsets.only(top: 8), child: _buildResultado(_resultado!)),
        const SizedBox(height: 24),
        ProviderCodeCard(
          token: widget.token,
          visitorQrService: widget.visitorQrService,
          propertyService: widget.propertyService,
        ),
      ],
    );
  }

  // Lo que el propio QR ya trae escrito, leído SIN conexión — antes de saber si el servidor lo acepta.
  Widget _buildInfoOffline(VisitorQrOfflineInfo info) {
    return Card(
      key: const Key('info_offline_qr'),
      color: Colors.blue.withValues(alpha: 0.08),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Datos del código (leídos sin conexión) — corrobóralos con el visitante:', style: TextStyle(fontWeight: FontWeight.bold)),
            if (info.nombreVisitante != null) Text('Visitante: ${info.nombreVisitante}'),
            if (info.numeroPersonas != null)
              Text('${info.numeroPersonas} persona${info.numeroPersonas == 1 ? '' : 's'}'),
            if (info.vivienda != null) Text('Va a: ${info.vivienda}'),
            if (info.nombreResidente != null) Text('Lo invita: ${info.nombreResidente}'),
          ],
        ),
      ),
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
                    if (resultado.nombreVisitante != null) Text('Visitante: ${resultado.nombreVisitante}'),
                    if (resultado.numeroPersonas != null)
                      Text('${resultado.numeroPersonas} persona${resultado.numeroPersonas == 1 ? '' : 's'}'),
                    Text(
                      resultado.vivienda != null ? 'Va a: ${resultado.vivienda}' : 'Servicio al condominio en general',
                      key: const Key('destino_qr'),
                    ),
                    if (resultado.nombreResidente != null) Text('Lo invita: ${resultado.nombreResidente}'),
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
