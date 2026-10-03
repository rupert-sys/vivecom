import 'package:flutter/material.dart';

import 'theme.dart';

import 'screens/bloqueo_biometrico_screen.dart';
import 'screens/login_screen.dart';
import 'screens/residente_home_screen.dart';
import 'services/amenity_service.dart';
import 'services/announcement_service.dart';
import 'services/auth_service.dart';
import 'services/cash_movement_service.dart';
import 'services/clabe_service.dart';
import 'services/expense_service.dart';
import 'services/fee_service.dart';
import 'services/lost_found_service.dart';
import 'services/payment_agreement_service.dart';
import 'services/payment_proof_service.dart';
import 'services/poll_service.dart';
import 'services/property_service.dart';
import 'services/receipt_service.dart';
import 'services/reservation_service.dart';
import 'services/statement_service.dart';
import 'services/tenant_service.dart';
import 'services/visit_service.dart';
import 'widgets/oculta_teclado.dart';

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
  final TenantService _tenantService = TenantService();
  final ClabeService _clabeService = ClabeService();
  final PropertyService _propertyService = PropertyService();
  final FeeService _feeService = FeeService();
  final ReceiptService _receiptService = ReceiptService();
  final ExpenseService _expenseService = ExpenseService();
  final CashMovementService _cashMovementService = CashMovementService();
  final AnnouncementService _announcementService = AnnouncementService();
  final PollService _pollService = PollService();
  final LostFoundService _lostFoundService = LostFoundService();
  final AmenityService _amenityService = AmenityService();
  final ReservationService _reservationService = ReservationService();
  final VisitService _visitService = VisitService();
  final PaymentProofService _proofService = PaymentProofService();
  final PaymentAgreementService _agreementService = PaymentAgreementService();

  String? _token;
  TokenPayload? _usuario;
  bool _cargandoSesion = true;
  // true si hay sesión guardada Y el residente activó Face ID/huella (ver AuthService.biometricosActivados) —
  // la sesión existe pero no se usa hasta pasar BloqueoBiometricoScreen. Se apaga al desbloquear (dura lo que
  // dura la app abierta: la próxima vez que se abra de cero, se vuelve a pedir).
  bool _necesitaDesbloqueo = false;

  @override
  void initState() {
    super.initState();
    _restaurarSesion();
  }

  Future<void> _restaurarSesion() async {
    final token = await _authService.obtenerToken();
    final necesitaDesbloqueo = token != null && await _authService.biometricosActivados();
    setState(() {
      _token = token;
      _usuario = token != null ? TokenPayload.decode(token) : null;
      _necesitaDesbloqueo = necesitaDesbloqueo;
      _cargandoSesion = false;
    });
  }

  Future<void> _onLogout() async {
    await _authService.logout();
    setState(() {
      _token = null;
      _usuario = null;
      _necesitaDesbloqueo = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vivecom',
      theme: temaVivecom,
      builder: (context, child) => OcultaTecladoAlTocarFuera(child: child),
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

    if (_necesitaDesbloqueo) {
      return BloqueoBiometricoScreen(
        onDesbloqueado: () => setState(() => _necesitaDesbloqueo = false),
        onCerrarSesion: _onLogout,
      );
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
      tenantService: _tenantService,
      clabeService: _clabeService,
      propertyService: _propertyService,
      feeService: _feeService,
      receiptService: _receiptService,
      expenseService: _expenseService,
      cashMovementService: _cashMovementService,
      announcementService: _announcementService,
      pollService: _pollService,
      lostFoundService: _lostFoundService,
      amenityService: _amenityService,
      reservationService: _reservationService,
      visitService: _visitService,
      proofService: _proofService,
      agreementService: _agreementService,
      onLogout: _onLogout,
    );
  }
}
