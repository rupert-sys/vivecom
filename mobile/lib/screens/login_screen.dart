import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/biometric_auth_service.dart';
import '../widgets/instalar_app.dart';
import 'registro_screen.dart';

class LoginScreen extends StatefulWidget {
  final AuthService authService;
  final VoidCallback onLoginSuccess;
  final BiometricAuthService? biometricService;
  // Bajar el APK (Android) o añadir la app a la pantalla de inicio (iPhone): solo aparece en la versión web.
  final Widget instalarApp;

  const LoginScreen({
    super.key,
    required this.authService,
    required this.onLoginSuccess,
    this.biometricService,
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
  bool _recordar = false;
  late final BiometricAuthService _biometricService;

  @override
  void initState() {
    super.initState();
    _biometricService = widget.biometricService ?? BiometricAuthService();
  }

  Future<void> _iniciarSesion() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      await widget.authService.login(
        _emailController.text.trim(), _passwordController.text, recordar: _recordar,
      );
      // _cargando se apaga AQUÍ, no en un finally al final: _ofrecerBiometricos() espera a que el residente
      // conteste un diálogo, y mientras tanto un spinner detrás no tiene sentido — además, gira sin parar
      // (nunca "se asienta"), así que dejarlo prendido colgaría cualquier pumpAndSettle() de las pruebas.
      if (mounted) setState(() => _cargando = false);
      await _ofrecerBiometricos();
      widget.onLoginSuccess();
    } catch (err) {
      if (mounted) {
        setState(() {
          _error = err is ApiException ? err.message : 'No se pudo iniciar sesión.';
          _cargando = false;
        });
      }
    }
  }

  // Se ofrece una sola vez por login manual (no en cada apertura de la app: quien ya dijo que no, no se le
  // vuelve a preguntar hasta que cierre sesión y entre de nuevo con contraseña) — ver
  // AuthService.biometricosActivados.
  Future<void> _ofrecerBiometricos() async {
    if (!mounted) return;
    if (await widget.authService.biometricosActivados()) return;
    if (!await _biometricService.estaDisponible()) return;
    if (!mounted) return;
    final activar = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Entrar más rápido'),
        content: const Text('¿Quieres usar Face ID o tu huella para entrar la próxima vez, sin escribir tu contraseña?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Ahora no')),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Sí, activar')),
        ],
      ),
    );
    if (activar == true) {
      await widget.authService.activarBiometricos();
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
                  CheckboxListTile(
                    key: const Key('recordar_checkbox'),
                    value: _recordar,
                    onChanged: (valor) => setState(() => _recordar = valor ?? false),
                    title: const Text('Recordarme'),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                  ),
                  const SizedBox(height: 12),
                  _cargando
                      ? const Center(child: CircularProgressIndicator())
                      : ElevatedButton(onPressed: _iniciarSesion, child: const Text('Entrar')),
                  const SizedBox(height: 12),
                  TextButton(
                    key: const Key('ir_a_registro'),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => RegistroScreen(
                          authService: widget.authService,
                          onRegistroExitoso: () {
                            Navigator.of(context).pop();
                            widget.onLoginSuccess();
                          },
                        ),
                      ),
                    ),
                    child: const Text('¿Tu vivienda no tiene cuenta todavía? Regístrate'),
                  ),
                  const SizedBox(height: 12),
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
