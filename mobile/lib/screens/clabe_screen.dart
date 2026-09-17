import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/tenant_clabe.dart';
import '../services/api_client.dart';
import '../services/clabe_service.dart';

class ClabeScreen extends StatefulWidget {
  final String token;
  final ClabeService clabeService;

  const ClabeScreen({super.key, required this.token, required this.clabeService});

  @override
  State<ClabeScreen> createState() => _ClabeScreenState();
}

class _ClabeScreenState extends State<ClabeScreen> {
  TenantClabe? _clabe;
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
      final clabe = await widget.clabeService.obtenerClabe(widget.token);
      if (!mounted) return;
      setState(() => _clabe = clabe);
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudo cargar la CLABE.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _copiarClabe() async {
    final clabe = _clabe;
    if (clabe == null) return;
    await Clipboard.setData(ClipboardData(text: clabe.clabeDestino));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('CLABE copiada')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cuenta CLABE')),
      body: RefreshIndicator(onRefresh: _cargar, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_cargando && _clabe == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _clabe == null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        ],
      );
    }
    return _buildContenido(_clabe!);
  }

  // No hay un campo "banco" en el backend (Tenant solo guarda nombre y
  // clabe_destino, ver app/models/tenant.py) — el panel admin web
  // (ClabePage.tsx, F1-20) tampoco lo muestra. Se refleja tal cual el
  // contrato real en vez de inventar un dato que no existe.
  Widget _buildContenido(TenantClabe clabe) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Transfiere tu cuota a esta cuenta:', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(clabe.nombre, style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 24),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('CLABE vigente', style: Theme.of(context).textTheme.labelMedium),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        clabe.clabeDestino,
                        key: const Key('clabe_destino'),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    IconButton(icon: const Icon(Icons.copy), tooltip: 'Copiar CLABE', onPressed: _copiarClabe),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
