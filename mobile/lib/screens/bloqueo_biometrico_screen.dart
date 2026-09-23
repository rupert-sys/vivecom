import 'package:flutter/material.dart';

import '../services/biometric_auth_service.dart';

// Se muestra al abrir la app cuando ya hay una sesión guardada y el residente activó Face ID/huella (ver
// AuthService.biometricosActivados) — la sesión sigue ahí (el token no se toca), solo hace falta pasar la
// verificación biométrica para poder usarla. Un rechazo o "cancelar" no cierra la sesión: se puede reintentar,
// o salir por completo con "Cerrar sesión" (esa sí la maneja quien nos crea: onCerrarSesion es responsable de
// llamar AuthService.logout(), que además apaga la propia preferencia de biométricos).
class BloqueoBiometricoScreen extends StatefulWidget {
  final BiometricAuthService? biometricService;
  final VoidCallback onDesbloqueado;
  final VoidCallback onCerrarSesion;

  const BloqueoBiometricoScreen({
    super.key,
    required this.onDesbloqueado,
    required this.onCerrarSesion,
    this.biometricService,
  });

  @override
  State<BloqueoBiometricoScreen> createState() => _BloqueoBiometricoScreenState();
}

class _BloqueoBiometricoScreenState extends State<BloqueoBiometricoScreen> {
  late final BiometricAuthService _biometricService;
  bool _verificando = false;
  bool _fallo = false;

  @override
  void initState() {
    super.initState();
    _biometricService = widget.biometricService ?? BiometricAuthService();
    WidgetsBinding.instance.addPostFrameCallback((_) => _desbloquear());
  }

  Future<void> _desbloquear() async {
    setState(() {
      _verificando = true;
      _fallo = false;
    });
    final exito = await _biometricService.autenticar('Confirma tu identidad para entrar a Vivecom');
    if (!mounted) return;
    setState(() => _verificando = false);
    if (exito) {
      widget.onDesbloqueado();
    } else {
      setState(() => _fallo = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.lock_outline, size: 64),
              const SizedBox(height: 16),
              const Text('Vivecom', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 24),
              if (_verificando) const CircularProgressIndicator(),
              if (!_verificando && _fallo) ...[
                const Text('No se pudo confirmar tu identidad.', style: TextStyle(color: Colors.red)),
                const SizedBox(height: 16),
                ElevatedButton(onPressed: _desbloquear, child: const Text('Intentar de nuevo')),
              ],
              const SizedBox(height: 12),
              TextButton(onPressed: widget.onCerrarSesion, child: const Text('Cerrar sesión')),
            ],
          ),
        ),
      ),
    );
  }
}
