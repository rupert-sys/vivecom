import 'package:flutter/material.dart';

import '../services/clabe_service.dart';
import '../services/fee_service.dart';
import '../services/property_service.dart';
import '../services/statement_service.dart';
import 'clabe_screen.dart';
import 'payment_screen.dart';
import 'statement_screen.dart';

// Shell de navegación de la app residente: cada pantalla (F1-24, F1-25, ...)
// se agrega aquí como un destino más, sin tocar sus Scaffold/AppBar propios.
class ResidenteHomeScreen extends StatefulWidget {
  final String propertyId;
  final String token;
  final StatementService statementService;
  final ClabeService clabeService;
  final PropertyService propertyService;
  final FeeService feeService;
  final VoidCallback onLogout;

  const ResidenteHomeScreen({
    super.key,
    required this.propertyId,
    required this.token,
    required this.statementService,
    required this.clabeService,
    required this.propertyService,
    required this.feeService,
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
          NavigationDestination(icon: Icon(Icons.account_balance), label: 'CLABE'),
        ],
      ),
    );
  }
}
