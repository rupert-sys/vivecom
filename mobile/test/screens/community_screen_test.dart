import 'package:app_residente/screens/community_screen.dart';
import 'package:app_residente/services/amenity_service.dart';
import 'package:app_residente/services/announcement_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/lost_found_service.dart';
import 'package:app_residente/services/poll_service.dart';
import 'package:app_residente/services/reservation_service.dart';
import 'package:app_residente/services/visit_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('muestra las 5 pestañas de la comunidad y cambia entre ellas', (tester) async {
    final mockClient = MockClient((request) async => http.Response('[]', 200));
    final api = ApiClient(client: mockClient);

    await tester.pumpWidget(
      MaterialApp(
        home: CommunityScreen(
          token: 'un-token',
          announcementService: AnnouncementService(api: api),
          pollService: PollService(api: api),
          lostFoundService: LostFoundService(api: api),
          amenityService: AmenityService(api: api),
          reservationService: ReservationService(api: api),
          visitService: VisitService(api: api),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Comunidad'), findsOneWidget);
    expect(find.text('Avisos'), findsOneWidget);
    expect(find.text('Votaciones'), findsOneWidget);
    expect(find.text('Visitas y paquetes'), findsOneWidget);
    expect(find.text('Objetos perdidos'), findsOneWidget);
    expect(find.text('Reservaciones'), findsOneWidget);
    expect(find.text('Todavía no hay avisos.'), findsOneWidget);

    await tester.tap(find.text('Votaciones'));
    await tester.pumpAndSettle();
    expect(find.text('Todavía no hay votaciones.'), findsOneWidget);

    await tester.ensureVisible(find.text('Objetos perdidos'));
    await tester.tap(find.text('Objetos perdidos'));
    await tester.pumpAndSettle();
    expect(find.text('Todavía no hay publicaciones autorizadas.'), findsOneWidget);

    await tester.ensureVisible(find.text('Reservaciones'));
    await tester.tap(find.text('Reservaciones'));
    await tester.pumpAndSettle();
    expect(find.text('Todavía no hay amenidades configuradas.'), findsOneWidget);
  });
}
