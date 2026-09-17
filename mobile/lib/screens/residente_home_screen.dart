import 'package:flutter/material.dart';

import '../services/amenity_service.dart';
import '../services/announcement_service.dart';
import '../services/clabe_service.dart';
import '../services/expense_service.dart';
import '../services/fee_service.dart';
import '../services/lost_found_service.dart';
import '../services/poll_service.dart';
import '../services/property_service.dart';
import '../services/receipt_service.dart';
import '../services/reservation_service.dart';
import '../services/statement_service.dart';
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
    required this.onLogout,
  });

  @override
  State<ResidenteHomeScreen> createState() => _ResidenteHomeScreenState();
}

class _ResidenteHomeScreenState extends State<ResidenteHomeScreen> {
  int _indiceSeleccionado = 0;

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
      ),
      ClabeScreen(token: widget.token, clabeService: widget.clabeService),
    ];

    return Scaffold(
      body: IndexedStack(index: _indiceSeleccionado, children: pantallas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _indiceSeleccionado,
        onDestinationSelected: (indice) => setState(() => _indiceSeleccionado = indice),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.account_balance_wallet), label: 'Estado de cuenta'),
          NavigationDestination(icon: Icon(Icons.payments), label: 'Pago'),
          NavigationDestination(icon: Icon(Icons.history), label: 'Historial'),
          NavigationDestination(icon: Icon(Icons.receipt_long), label: 'Gastos'),
          NavigationDestination(icon: Icon(Icons.groups), label: 'Comunidad'),
          NavigationDestination(icon: Icon(Icons.account_balance), label: 'CLABE'),
        ],
      ),
    );
  }
}
