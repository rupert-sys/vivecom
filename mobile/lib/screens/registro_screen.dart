import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/resident_activation_service.dart';

// Alta por /signup (landing de bienvenida del panel admin): cada vivienda nace con una cuenta SIN activar
// (casa<n>@dominio) — aquí el residente la reclama con sus propios datos y contraseña. GET
// /residents/activar/preview confirma en vivo a qué correo quedará ligada su vivienda, antes de llenar el
// resto, para que el residente note un número de casa equivocado ANTES de registrarse con el equivocado.
class RegistroScreen extends StatefulWidget {
  final AuthService authService;
  final ResidentActivationService? activationService;
  final VoidCallback onRegistroExitoso;

  const RegistroScreen({
    super.key,
    required this.authService,
    required this.onRegistroExitoso,
    this.activationService,
  });

  @override
  State<RegistroScreen> createState() => _RegistroScreenState();
}

class _RegistroScreenState extends State<RegistroScreen> {
  final _condominioController = TextEditingController();
  final _casaController = TextEditingController();
  final _nombreController = TextEditingController();
  final _telefonoController = TextEditingController();
  final _correoController = TextEditingController();
  final _passwordController = TextEditingController();
  final _casaFocus = FocusNode();

  String _rol = 'propietario';
  String? _previewEmail;
  String? _previewError;
  bool _verificando = false;
  String? _error;
  bool _registrando = false;

  late final ResidentActivationService _activationService;

  @override
  void initState() {
    super.initState();
    _activationService = widget.activationService ?? ResidentActivationService();
    _casaFocus.addListener(() {
      if (!_casaFocus.hasFocus) _verificarVivienda();
    });
  }

  Future<void> _verificarVivienda() async {
    final condominio = _condominioController.text.trim();
    final numero = int.tryParse(_casaController.text.trim());
    if (condominio.isEmpty || numero == null) {
      setState(() {
        _previewEmail = null;
        _previewError = null;
      });
      return;
    }
    setState(() {
      _verificando = true;
      _previewError = null;
    });
    try {
      final preview = await _activationService.preview(nombreCondominio: condominio, numeroDeCasa: numero);
      if (!mounted) return;
      setState(() => _previewEmail = preview.email);
    } catch (err) {
      if (!mounted) return;
      setState(() {
        _previewEmail = null;
        _previewError = err is ApiException ? err.message : 'No se pudo verificar la vivienda.';
      });
    } finally {
      if (mounted) setState(() => _verificando = false);
    }
  }

  Future<void> _registrar() async {
    setState(() {
      _registrando = true;
      _error = null;
    });
    try {
      final numero = int.parse(_casaController.text.trim());
      final token = await _activationService.activar(
        nombreCondominio: _condominioController.text.trim(),
        numeroDeCasa: numero,
        nombreCompleto: _nombreController.text.trim(),
        rol: _rol,
        telefono: _telefonoController.text.trim(),
        correo: _correoController.text.trim(),
        password: _passwordController.text,
      );
      await widget.authService.guardarToken(token);
      widget.onRegistroExitoso();
    } catch (err) {
      setState(() {
        _error = err is ApiException ? err.message : 'No se pudo completar el registro.';
      });
    } finally {
      if (mounted) setState(() => _registrando = false);
    }
  }

  bool get _puedeRegistrar => _previewEmail != null && _nombreController.text.trim().isNotEmpty &&
      _telefonoController.text.trim().isNotEmpty && _passwordController.text.length >= 8;

  @override
  void dispose() {
    _condominioController.dispose();
    _casaController.dispose();
    _nombreController.dispose();
    _telefonoController.dispose();
    _correoController.dispose();
    _passwordController.dispose();
    _casaFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Regístrate como residente')),
      body: Center(
        child: SingleChildScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Este campo NO da de alta un condominio — eso lo hace el administrador aparte (landing de
                  // bienvenida del panel). Aquí solo identifica cuál, entre los que ya existen, es el tuyo.
                  const Text(
                    'Tu condominio ya debe estar dado de alta por su administrador. Dinos cuál es y tu número de casa para encontrar tu vivienda.',
                    style: TextStyle(color: Colors.grey, fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('condominio_field'),
                    controller: _condominioController,
                    decoration: const InputDecoration(labelText: '¿En qué condominio vives?'),
                    onSubmitted: (_) => _verificarVivienda(),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('casa_field'),
                    controller: _casaController,
                    focusNode: _casaFocus,
                    decoration: const InputDecoration(labelText: 'Número de casa'),
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 8),
                  if (_verificando) const Text('Verificando…', style: TextStyle(color: Colors.grey)),
                  if (!_verificando && _previewEmail != null)
                    Text('Tu usuario será: $_previewEmail', style: const TextStyle(color: Colors.green)),
                  if (!_verificando && _previewError != null)
                    Text(_previewError!, style: const TextStyle(color: Colors.red)),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('nombre_field'),
                    controller: _nombreController,
                    decoration: const InputDecoration(labelText: 'Nombre y apellidos'),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    key: const Key('rol_field'),
                    initialValue: _rol,
                    decoration: const InputDecoration(labelText: '¿Eres dueño o rentas?'),
                    items: const [
                      DropdownMenuItem(value: 'propietario', child: Text('Soy dueño')),
                      DropdownMenuItem(value: 'inquilino', child: Text('Rento')),
                    ],
                    onChanged: (v) => setState(() => _rol = v ?? 'propietario'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('telefono_field'),
                    controller: _telefonoController,
                    decoration: const InputDecoration(labelText: 'Teléfono'),
                    keyboardType: TextInputType.phone,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('correo_field'),
                    controller: _correoController,
                    decoration: const InputDecoration(labelText: 'Correo (opcional)'),
                    keyboardType: TextInputType.emailAddress,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('password_field'),
                    controller: _passwordController,
                    decoration: const InputDecoration(labelText: 'Elige una contraseña (mínimo 8 caracteres)'),
                    obscureText: true,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 24),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(_error!, style: const TextStyle(color: Colors.red)),
                    ),
                  _registrando
                      ? const Center(child: CircularProgressIndicator())
                      : ElevatedButton(
                          onPressed: _puedeRegistrar ? _registrar : null,
                          child: const Text('Registrarme'),
                        ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
