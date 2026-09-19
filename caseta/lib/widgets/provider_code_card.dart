import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../models/property.dart';
import '../models/visitor_qr_validation.dart';
import '../services/api_client.dart';
import '../services/property_service.dart';
import '../services/visitor_qr_service.dart';

// El guardia emite un código de un solo uso para un proveedor (plomero,
// jardinero, mensajería): el proveedor lo enseña y el guardia lo valida al
// escanearlo, con lo que queda a quién se dejó pasar y a dónde. Reglamento
// Art. 17 V.3: el acceso de proveedores requiere autorización.
class ProviderCodeCard extends StatefulWidget {
  final String token;
  final VisitorQrService visitorQrService;
  final PropertyService propertyService;

  const ProviderCodeCard({
    super.key,
    required this.token,
    required this.visitorQrService,
    required this.propertyService,
  });

  @override
  State<ProviderCodeCard> createState() => _ProviderCodeCardState();
}

class _ProviderCodeCardState extends State<ProviderCodeCard> {
  final _descripcionController = TextEditingController();
  List<Property> _propiedades = [];
  String? _propertyId;
  bool _emitiendo = false;
  String? _error;
  ProviderCode? _codigo;

  @override
  void initState() {
    super.initState();
    _cargarPropiedades();
  }

  @override
  void dispose() {
    _descripcionController.dispose();
    super.dispose();
  }

  Future<void> _cargarPropiedades() async {
    try {
      final propiedades = await widget.propertyService.listarPropiedades(widget.token);
      if (!mounted) return;
      setState(() => _propiedades = propiedades);
    } catch (_) {
      // Sin conexión no se puede emitir el código de todos modos.
    }
  }

  Future<void> _emitir() async {
    final descripcion = _descripcionController.text.trim();
    if (descripcion.isEmpty) {
      setState(() => _error = 'Anota quién es el proveedor (nombre o empresa).');
      return;
    }
    setState(() {
      _emitiendo = true;
      _error = null;
    });
    try {
      final codigo = await widget.visitorQrService.emitirCodigoProveedor(descripcion, _propertyId, widget.token);
      if (!mounted) return;
      setState(() => _codigo = codigo);
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudo emitir el código (requiere conexión).');
    } finally {
      if (mounted) setState(() => _emitiendo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final codigo = _codigo;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Código para proveedor', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Sirve una sola vez. Al escanearlo queda registrado a quién se dejó pasar.'),
            const SizedBox(height: 8),
            TextField(
              key: const Key('proveedor_descripcion_field'),
              controller: _descripcionController,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Proveedor (nombre o empresa)'),
            ),
            const SizedBox(height: 8),
            DropdownButton<String?>(
              key: const Key('proveedor_vivienda_dropdown'),
              value: _propertyId,
              isExpanded: true,
              hint: const Text('Vivienda que visita (opcional)'),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('Servicio al condominio en general')),
                ..._propiedades.map((p) => DropdownMenuItem<String?>(value: p.id, child: Text(p.identificador))),
              ],
              onChanged: (valor) => setState(() => _propertyId = valor),
            ),
            if (_error != null)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text(_error!, style: const TextStyle(color: Colors.red))),
            const SizedBox(height: 8),
            ElevatedButton.icon(
              onPressed: _emitiendo ? null : _emitir,
              icon: const Icon(Icons.qr_code),
              label: Text(_emitiendo ? 'Emitiendo…' : 'Emitir código'),
            ),
            if (codigo != null) ...[
              const SizedBox(height: 12),
              Center(
                child: Container(
                  key: const Key('qr_proveedor'),
                  color: Colors.white,
                  padding: const EdgeInsets.all(8),
                  child: QrImageView(key: Key('qr_${codigo.codigo}'), data: codigo.codigo, size: 180),
                ),
              ),
              const SizedBox(height: 8),
              Center(child: Text(codigo.descripcion, style: const TextStyle(fontWeight: FontWeight.bold))),
              Center(child: SelectableText(codigo.codigo, key: const Key('codigo_proveedor'))),
            ],
          ],
        ),
      ),
    );
  }
}
