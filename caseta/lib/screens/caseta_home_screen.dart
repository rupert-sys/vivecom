import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';

import '../db/app_database.dart';
import '../services/access_log_service.dart';
import '../services/property_service.dart';
import '../services/sync_service.dart';
import '../services/visitor_qr_service.dart';
import 'access_log_screen.dart';
import 'incident_screen.dart';
import 'qr_scan_screen.dart';

// Shell de navegación de la app caseta (F2-07 a F2-10): registro de
// accesos, incidencias y validación de QR de visitantes, con un indicador
// de conectividad/pendientes siempre visible — es lo primero que un guardia
// necesita saber ("¿se está sincronizando lo que ya capturé?").
class CasetaHomeScreen extends StatefulWidget {
  final String token;
  final AppDatabase db;
  final PropertyService propertyService;
  final AccessLogService accessLogService;
  final VisitorQrService visitorQrService;
  final SyncService syncService;
  final VoidCallback onLogout;

  const CasetaHomeScreen({
    super.key,
    required this.token,
    required this.db,
    required this.propertyService,
    required this.accessLogService,
    required this.visitorQrService,
    required this.syncService,
    required this.onLogout,
  });

  @override
  State<CasetaHomeScreen> createState() => _CasetaHomeScreenState();
}

class _CasetaHomeScreenState extends State<CasetaHomeScreen> {
  int _indiceSeleccionado = 0;

  @override
  Widget build(BuildContext context) {
    final pantallas = [
      AccessLogScreen(
        token: widget.token,
        db: widget.db,
        propertyService: widget.propertyService,
        accessLogService: widget.accessLogService,
        syncService: widget.syncService,
      ),
      IncidentScreen(db: widget.db, syncService: widget.syncService),
      QrScanScreen(token: widget.token, visitorQrService: widget.visitorQrService),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Vivecom Caseta'),
        actions: [
          _ConectividadIndicador(db: widget.db),
          IconButton(icon: const Icon(Icons.logout), onPressed: widget.onLogout),
        ],
      ),
      body: IndexedStack(index: _indiceSeleccionado, children: pantallas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _indiceSeleccionado,
        onDestinationSelected: (indice) => setState(() => _indiceSeleccionado = indice),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.login), label: 'Accesos'),
          NavigationDestination(icon: Icon(Icons.report_problem), label: 'Incidencias'),
          NavigationDestination(icon: Icon(Icons.qr_code_scanner), label: 'QR visitante'),
        ],
      ),
    );
  }
}

class _ConectividadIndicador extends StatelessWidget {
  final AppDatabase db;
  const _ConectividadIndicador({required this.db});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<List<ConnectivityResult>>(
      stream: Connectivity().onConnectivityChanged,
      builder: (context, conexionSnapshot) {
        final enLinea = !(conexionSnapshot.data?.every((r) => r == ConnectivityResult.none) ?? false);
        return StreamBuilder<List<PendingAccessLog>>(
          stream: db.watchAccesos(),
          builder: (context, accesosSnapshot) {
            return StreamBuilder<List<PendingIncident>>(
              stream: db.watchIncidencias(),
              builder: (context, incidenciasSnapshot) {
                final pendientes =
                    (accesosSnapshot.data ?? []).where((a) => a.syncStatus == 'pending').length +
                    (incidenciasSnapshot.data ?? []).where((i) => i.syncStatus == 'pending').length;
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    children: [
                      Icon(
                        enLinea ? Icons.cloud_done : Icons.cloud_off,
                        key: Key(enLinea ? 'conectividad_online' : 'conectividad_offline'),
                        size: 20,
                      ),
                      if (pendientes > 0)
                        Padding(
                          padding: const EdgeInsets.only(left: 4),
                          child: Text('$pendientes', key: const Key('contador_pendientes')),
                        ),
                    ],
                  ),
                );
              },
            );
          },
        );
      },
    );
  }
}
