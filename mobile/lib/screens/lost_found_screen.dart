import 'package:flutter/material.dart';

import '../models/lost_found_item.dart';
import '../services/api_client.dart';
import '../services/lost_found_service.dart';

class LostFoundScreen extends StatefulWidget {
  final String token;
  final LostFoundService lostFoundService;

  const LostFoundScreen({super.key, required this.token, required this.lostFoundService});

  @override
  State<LostFoundScreen> createState() => _LostFoundScreenState();
}

class _LostFoundScreenState extends State<LostFoundScreen> {
  List<LostFoundItem>? _objetos;
  String? _error;
  bool _cargando = true;

  final _descripcionController = TextEditingController();
  final _fotoUrlController = TextEditingController();
  bool _publicando = false;
  String? _errorPublicar;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _descripcionController.dispose();
    _fotoUrlController.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final objetos = await widget.lostFoundService.listarObjetos(widget.token);
      if (!mounted) return;
      setState(() => _objetos = objetos);
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudieron cargar los objetos.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _publicar() async {
    if (_descripcionController.text.trim().isEmpty) return;
    setState(() {
      _publicando = true;
      _errorPublicar = null;
    });
    try {
      await widget.lostFoundService.publicarObjeto(
        _descripcionController.text.trim(),
        _fotoUrlController.text.trim().isEmpty ? null : _fotoUrlController.text.trim(),
        widget.token,
      );
      _descripcionController.clear();
      _fotoUrlController.clear();
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Publicado. Aparecerá aquí cuando el administrador lo autorice.')));
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorPublicar = err is ApiException ? err.message : 'No se pudo publicar.');
    } finally {
      if (mounted) setState(() => _publicando = false);
    }
  }

  // Sin Scaffold/AppBar propios: ver la nota en announcements_screen.dart.
  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _cargar,
      child: ListView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: const EdgeInsets.all(16),
        children: [
          _buildFormularioPublicar(),
          const SizedBox(height: 24),
          Text('Publicaciones autorizadas', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _buildLista(),
        ],
      ),
    );
  }

  Widget _buildFormularioPublicar() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Publicar un objeto encontrado o perdido'),
            const SizedBox(height: 8),
            TextField(
              key: const Key('descripcion_field'),
              controller: _descripcionController,
              decoration: const InputDecoration(labelText: 'Descripción'),
            ),
            const SizedBox(height: 8),
            TextField(
              key: const Key('foto_url_field'),
              controller: _fotoUrlController,
              decoration: const InputDecoration(labelText: 'URL de foto (opcional)'),
            ),
            if (_errorPublicar != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_errorPublicar!, style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 8),
            ElevatedButton(onPressed: _publicando ? null : _publicar, child: Text(_publicando ? 'Publicando…' : 'Publicar')),
          ],
        ),
      ),
    );
  }

  Widget _buildLista() {
    if (_cargando && _objetos == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _objetos == null) {
      return Text(_error!, style: const TextStyle(color: Colors.red));
    }
    final objetos = _objetos!;
    if (objetos.isEmpty) {
      return const Text('Todavía no hay publicaciones autorizadas.');
    }
    return Column(
      children: objetos
          .map(
            (objeto) => ListTile(
              title: Text(objeto.descripcion),
              subtitle: objeto.fotoUrl != null ? Text(objeto.fotoUrl!) : null,
            ),
          )
          .toList(),
    );
  }
}
