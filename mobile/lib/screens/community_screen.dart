import 'package:flutter/material.dart';

import '../services/amenity_service.dart';
import '../services/announcement_service.dart';
import '../services/lost_found_service.dart';
import '../services/poll_service.dart';
import '../services/reservation_service.dart';
import '../services/visit_service.dart';
import 'announcements_screen.dart';
import 'lost_found_screen.dart';
import 'polls_screen.dart';
import 'reservations_screen.dart';
import 'visits_screen.dart';

// Agrupa las secciones "comunitarias" (avisos, votaciones, visitas y
// paquetes, reservaciones, objetos perdidos) bajo una sola pestaña de la barra de navegación
// principal — con 4 pantallas más, sumarlas todas de forma plana a
// ResidenteHomeScreen habría dejado la barra inferior con 9 destinos,
// inusable en un teléfono real (F2-19). Las 4 pantallas hijas ya no traen
// su propio Scaffold/AppBar (ver la nota en cada una) — este widget aporta
// el único AppBar+TabBar compartido.
class CommunityScreen extends StatelessWidget {
  final String token;
  final AnnouncementService announcementService;
  final PollService pollService;
  final LostFoundService lostFoundService;
  final AmenityService amenityService;
  final ReservationService reservationService;
  final VisitService visitService;
  // Votaciones abiertas que esta vivienda aún no ha votado — se muestra como
  // insignia en la pestaña para que el residente sepa que hay algo por votar.
  final int votacionesPendientes;
  final ValueChanged<int>? onVotacionesPendientes;
  // Respuestas a mis dudas de avisos que aún no he visto (insignia en la pestaña Avisos).
  final int respuestasNuevas;
  final ValueChanged<int>? onRespuestasNuevas;

  const CommunityScreen({
    super.key,
    required this.token,
    required this.announcementService,
    required this.pollService,
    required this.lostFoundService,
    required this.amenityService,
    required this.reservationService,
    required this.visitService,
    this.votacionesPendientes = 0,
    this.onVotacionesPendientes,
    this.respuestasNuevas = 0,
    this.onRespuestasNuevas,
  });

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 5,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Comunidad'),
          bottom: TabBar(
            isScrollable: true,
            tabs: [
              Tab(
                child: Badge(
                  isLabelVisible: respuestasNuevas > 0,
                  label: Text('$respuestasNuevas'),
                  offset: const Offset(12, -8),
                  child: const Text('Avisos'),
                ),
              ),
              Tab(
                child: Badge(
                  isLabelVisible: votacionesPendientes > 0,
                  label: Text('$votacionesPendientes'),
                  offset: const Offset(12, -8),
                  child: const Text('Votaciones'),
                ),
              ),
              const Tab(text: 'Visitas y paquetes'),
              const Tab(text: 'Reservaciones'),
              const Tab(text: 'Objetos perdidos'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            AnnouncementsScreen(
              token: token,
              announcementService: announcementService,
              onRespuestasNuevas: onRespuestasNuevas,
            ),
            PollsScreen(token: token, pollService: pollService, onPendientesCambiaron: onVotacionesPendientes),
            VisitsScreen(token: token, visitService: visitService),
            ReservationsScreen(
              token: token,
              amenityService: amenityService,
              reservationService: reservationService,
            ),
            LostFoundScreen(token: token, lostFoundService: lostFoundService),
          ],
        ),
      ),
    );
  }
}
