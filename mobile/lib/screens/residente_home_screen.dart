import 'package:flutter/material.dart';

import '../services/amenity_service.dart';
import '../services/announcement_service.dart';
import '../services/clabe_service.dart';
import '../services/expense_service.dart';
import '../services/fee_service.dart';
import '../services/lost_found_service.dart';
import '../services/payment_agreement_service.dart';
import '../services/payment_proof_service.dart';
import '../services/poll_service.dart';
import '../services/property_service.dart';
import '../services/receipt_service.dart';
import '../services/reservation_service.dart';
import '../services/statement_service.dart';
import '../services/visit_service.dart';
import 'clabe_screen.dart';
import 'community_screen.dart';
import 'expenses_screen.dart';
import 'payment_history_screen.dart';
import 'payment_screen.dart';
import 'statement_screen.dart';

// Shell de navegación de la app residente: cada pantalla (F1-24, F1-25, ...)
// se agrega aquí como un destino más, sin tocar sus Scaffold/AppBar propios.
// Avisos/Votaciones/Objetos perdidos/Reservaciones se agrupan bajo la
// pestaña "Comunidad" (CommunityScreen, F2-19) en vez de sumarse cada una
// como destino plano.
class ResidenteHomeScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final ClabeService clabeService;
  final PropertyService propertyService;
  final FeeService feeService;
  final ReceiptService receiptService;
  final ExpenseService expenseService;
  final AnnouncementService announcementService;
  final PollService pollService;
  final LostFoundService lostFoundService;
  final AmenityService amenityService;
  final ReservationService reservationService;
  final VisitService visitService;
  final PaymentProofService proofService;
  final PaymentAgreementService agreementService;
  final VoidCallback onLogout;

  const ResidenteHomeScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.clabeService,
    required this.propertyService,
    required this.feeService,
    required this.receiptService,
    required this.expenseService,
    required this.announcementService,
    required this.pollService,
    required this.lostFoundService,
    required this.amenityService,
    required this.reservationService,
    required this.visitService,
    required this.proofService,
    required this.agreementService,
    required this.onLogout,
  });

  @override
  State<ResidenteHomeScreen> createState() => _ResidenteHomeScreenState();
}

class _ResidenteHomeScreenState extends State<ResidenteHomeScreen> {
  int _indiceSeleccionado = 0;
  // Votaciones abiertas por votar: se muestra como insignia en "Comunidad" para
  // que el residente sepa que hay una votación esperándolo sin buscarla.
  int _votacionesPendientes = 0;
  // Respuestas a mis dudas de avisos que aún no he visto: también se señalan en "Comunidad".
  int _respuestasNuevas = 0;

  @override
  void initState() {
    super.initState();
    _cargarVotacionesPendientes();
    _cargarRespuestasNuevas();
  }

  Future<void> _cargarRespuestasNuevas() async {
    try {
      final mias = await widget.announcementService.listarMisDudas(widget.token);
      if (mounted) setState(() => _respuestasNuevas = mias.where((d) => d.respuestaNueva).length);
    } catch (_) {
      // Solo un indicador; la pestaña de Avisos muestra sus propios errores.
    }
  }

  Future<void> _cargarVotacionesPendientes() async {
    try {
      final votaciones = await widget.pollService.listarVotaciones(widget.token);
      if (mounted) setState(() => _votacionesPendientes = votaciones.where((v) => v.pendienteDeVotar).length);
    } catch (_) {
      // Es solo un indicador; la pestaña de Votaciones muestra su propio error.
    }
  }

  @override
  Widget build(BuildContext context) {
    final pantallas = [
      StatementScreen(
        propertyId: widget.propertyId,
        token: widget.token,
        statementService: widget.statementService,
        onLogout: widget.onLogout,
      ),
      PaymentScreen(
        propertyId: widget.propertyId,
        token: widget.token,
        statementService: widget.statementService,
        propertyService: widget.propertyService,
        feeService: widget.feeService,
        clabeService: widget.clabeService,
        proofService: widget.proofService,
        agreementService: widget.agreementService,
      ),
      PaymentHistoryScreen(
        propertyId: widget.propertyId,
        token: widget.token,
        statementService: widget.statementService,
        receiptService: widget.receiptService,
      ),
      ExpensesScreen(token: widget.token, expenseService: widget.expenseService),
      CommunityScreen(
        token: widget.token,
        announcementService: widget.announcementService,
        pollService: widget.pollService,
        lostFoundService: widget.lostFoundService,
        amenityService: widget.amenityService,
        reservationService: widget.reservationService,
        visitService: widget.visitService,
        votacionesPendientes: _votacionesPendientes,
        onVotacionesPendientes: (n) {
          if (n != _votacionesPendientes) setState(() => _votacionesPendientes = n);
        },
        respuestasNuevas: _respuestasNuevas,
        onRespuestasNuevas: (n) {
          if (n != _respuestasNuevas) setState(() => _respuestasNuevas = n);
        },
      ),
      ClabeScreen(token: widget.token, clabeService: widget.clabeService),
    ];

    return Scaffold(
      body: IndexedStack(index: _indiceSeleccionado, children: pantallas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _indiceSeleccionado,
        onDestinationSelected: (indice) => setState(() => _indiceSeleccionado = indice),
        destinations: [
          NavigationDestination(icon: Icon(Icons.account_balance_wallet), label: 'Estado de cuenta'),
          NavigationDestination(icon: Icon(Icons.payments), label: 'Pago'),
          NavigationDestination(icon: Icon(Icons.history), label: 'Historial'),
          NavigationDestination(icon: Icon(Icons.receipt_long), label: 'Gastos'),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: _votacionesPendientes + _respuestasNuevas > 0,
              label: Text('${_votacionesPendientes + _respuestasNuevas}'),
              child: const Icon(Icons.groups),
            ),
            label: 'Comunidad',
          ),
          NavigationDestination(icon: Icon(Icons.account_balance), label: 'CLABE'),
        ],
      ),
    );
  }
}
