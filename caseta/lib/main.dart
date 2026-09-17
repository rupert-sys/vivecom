import 'package:flutter/material.dart';

import 'db/app_database.dart';
import 'screens/caseta_home_screen.dart';
import 'screens/login_screen.dart';
import 'services/access_log_service.dart';
import 'services/auth_service.dart';
import 'services/property_service.dart';
import 'services/sync_service.dart';
import 'services/visitor_qr_service.dart';

void main() {
  runApp(const VivecomCasetaApp());
}

class VivecomCasetaApp extends StatefulWidget {
  const VivecomCasetaApp({super.key});

  @override
  State<VivecomCasetaApp> createState() => _VivecomCasetaAppState();
}

class _VivecomCasetaAppState extends State<VivecomCasetaApp> {
  final AuthService _authService = AuthService();
  final AppDatabase _db = AppDatabase();
  final PropertyService _propertyService = PropertyService();
  final AccessLogService _accessLogService = AccessLogService();
  final VisitorQrService _visitorQrService = VisitorQrService();
  late final SyncService _syncService;

  String? _token;
  TokenPayload? _usuario;
  bool _cargandoSesion = true;

  @override
  void initState() {
    super.initState();
    _syncService = SyncService(db: _db, obtenerToken: () => _token ?? '');
    _syncService.iniciar();
    _restaurarSesion();
  }

  @override
  void dispose() {
    _syncService.detener();
    super.dispose();
  }

  Future<void> _restaurarSesion() async {
    final token = await _authService.obtenerToken();
    setState(() {
      _token = token;
      _usuario = token != null ? TokenPayload.decode(token) : null;
      _cargandoSesion = false;
    });
  }

  Future<void> _onLogout() async {
    await _authService.logout();
    setState(() {
      _token = null;
      _usuario = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vivecom Caseta',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2F6F63))),
      home: _buildHome(),
    );
  }

  Widget _buildHome() {
    if (_cargandoSesion) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final token = _token;
    final usuario = _usuario;

    if (token == null || usuario == null) {
      return LoginScreen(authService: _authService, onLoginSuccess: _restaurarSesion);
    }

    // F2-07: la app caseta es solo para guardia/admin — un residente que se
    // loguee aquí por error ve un mensaje claro, mismo criterio que
    // app_residente con un usuario de staff (mobile/lib/main.dart).
    if (usuario.rol != 'guardia' && usuario.rol != 'admin') {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Vivecom Caseta'),
          actions: [IconButton(icon: const Icon(Icons.logout), onPressed: _onLogout)],
        ),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Esta cuenta no tiene rol de guardia. La app caseta es solo para el personal de seguridad.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    return CasetaHomeScreen(
      token: token,
      db: _db,
      propertyService: _propertyService,
      accessLogService: _accessLogService,
      visitorQrService: _visitorQrService,
      syncService: _syncService,
      onLogout: _onLogout,
    );
  }
}
