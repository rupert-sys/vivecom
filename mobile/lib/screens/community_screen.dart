import 'package:flutter/material.dart';

import '../services/amenity_service.dart';
import '../services/announcement_service.dart';
import '../services/lost_found_service.dart';
import '../services/poll_service.dart';
import '../services/reservation_service.dart';
import 'announcements_screen.dart';
import 'lost_found_screen.dart';
import 'polls_screen.dart';
import 'reservations_screen.dart';

// Agrupa las secciones "comunitarias" (avisos, votaciones, objetos
// perdidos, reservaciones) bajo una sola pestaña de la barra de navegación
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

  const CommunityScreen({
    super.key,
    required this.token,
    required this.announcementService,
    required this.pollService,
    required this.lostFoundService,
    required this.amenityService,
    required this.reservationService,
  });

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Comunidad'),
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Avisos'),
              Tab(text: 'Votaciones'),
              Tab(text: 'Objetos perdidos'),
              Tab(text: 'Reservaciones'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            AnnouncementsScreen(token: token, announcementService: announcementService),
            PollsScreen(token: token, pollService: pollService),
            LostFoundScreen(token: token, lostFoundService: lostFoundService),
            ReservationsScreen(
              token: token,
              amenityService: amenityService,
              reservationService: reservationService,
            ),
          ],
        ),
      ),
    );
  }
}
