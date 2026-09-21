import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../widgets/instalar_app.dart';

class LoginScreen extends StatefulWidget {
  final AuthService authService;
  final VoidCallback onLoginSuccess;
  // Bajar el APK (Android) o añadir la app a la pantalla de inicio (iPhone): solo aparece en la versión web.
  final Widget instalarApp;

  const LoginScreen({
    super.key,
    required this.authService,
    required this.onLoginSuccess,
    this.instalarApp = const InstalarApp(),
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  String? _error;
  bool _cargando = false;

  Future<void> _iniciarSesion() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      await widget.authService.login(_emailController.text.trim(), _passwordController.text);
      widget.onLoginSuccess();
    } catch (err) {
      setState(() {
        _error = err is ApiException ? err.message : 'No se pudo iniciar sesión.';
      });
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vivecom')),
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
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(_error!, style: const TextStyle(color: Colors.red)),
                    ),
                  TextField(
                    key: const Key('email_field'),
                    controller: _emailController,
                    decoration: const InputDecoration(labelText: 'Email'),
                    keyboardType: TextInputType.emailAddress,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('password_field'),
                    controller: _passwordController,
                    decoration: const InputDecoration(labelText: 'Contraseña'),
                    obscureText: true,
                  ),
                  const SizedBox(height: 24),
                  _cargando
                      ? const Center(child: CircularProgressIndicator())
                      : ElevatedButton(onPressed: _iniciarSesion, child: const Text('Entrar')),
                  const SizedBox(height: 24),
                  widget.instalarApp,
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
