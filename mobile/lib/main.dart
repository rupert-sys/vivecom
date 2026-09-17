import 'package:flutter/material.dart';

import 'screens/login_screen.dart';
import 'screens/residente_home_screen.dart';
import 'services/announcement_service.dart';
import 'services/auth_service.dart';
import 'services/clabe_service.dart';
import 'services/expense_service.dart';
import 'services/fee_service.dart';
import 'services/property_service.dart';
import 'services/receipt_service.dart';
import 'services/statement_service.dart';

void main() {
  runApp(const VivecomApp());
}

class VivecomApp extends StatefulWidget {
  const VivecomApp({super.key});

  @override
  State<VivecomApp> createState() => _VivecomAppState();
}

class _VivecomAppState extends State<VivecomApp> {
  final AuthService _authService = AuthService();
  final StatementService _statementService = StatementService();
  final ClabeService _clabeService = ClabeService();
  final PropertyService _propertyService = PropertyService();
  final FeeService _feeService = FeeService();
  final ReceiptService _receiptService = ReceiptService();
  final ExpenseService _expenseService = ExpenseService();
  final AnnouncementService _announcementService = AnnouncementService();

  String? _token;
  TokenPayload? _usuario;
  bool _cargandoSesion = true;

  @override
  void initState() {
    super.initState();
    _restaurarSesion();
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
      title: 'Vivecom',
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

    // F1-24 es la app residente: solo tiene sentido para un usuario con
    // vivienda asociada. Un rol de staff (admin/tesorero/guardia) que se
    // loguee aquí por error ve un mensaje claro en vez de una 403 confusa
    // del backend.
    if (usuario.propertyId == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Vivecom'),
          actions: [IconButton(icon: const Icon(Icons.logout), onPressed: _onLogout)],
        ),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Esta cuenta no tiene una vivienda asociada. La app residente es solo para residentes.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    return ResidenteHomeScreen(
      propertyId: usuario.propertyId!,
      token: token,
      statementService: _statementService,
      clabeService: _clabeService,
      propertyService: _propertyService,
      feeService: _feeService,
      receiptService: _receiptService,
      expenseService: _expenseService,
      announcementService: _announcementService,
      onLogout: _onLogout,
    );
  }
}
