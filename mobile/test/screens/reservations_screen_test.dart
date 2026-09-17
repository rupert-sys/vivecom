import 'package:app_residente/screens/reservations_screen.dart';
import 'package:app_residente/services/amenity_service.dart';
import 'package:app_residente/services/api_client.dart';
import 'package:app_residente/services/reservation_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _fixtureAmenidades = '[{"id": "a1", "nombre": "Salón de fiestas", "periodo_limite_horas": 24}]';
const _fixtureReservaciones = '''
[
  {"id": "r1", "amenity_id": "a1", "property_id": "p1", "fecha_inicio": "2026-10-01T10:00:00",
   "fecha_fin": "2026-10-01T12:00:00", "estado": "pendiente", "aprobador_id": null}
]
''';

void main() {
  Future<void> pumpReservaciones(WidgetTester tester, http.Client client) async {
    final api = ApiClient(client: client);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ReservationsScreen(
            token: 'un-token',
            amenityService: AmenityService(api: api),
            reservationService: ReservationService(api: api),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('lista las amenidades disponibles y mis reservaciones', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(_fixtureAmenidades, 200);
      return http.Response(_fixtureReservaciones, 200);
    });

    await pumpReservaciones(tester, mockClient);

    expect(find.text('Solicitar reservación'), findsOneWidget);
    expect(find.byKey(const Key('amenidad_dropdown')), findsOneWidget);
    expect(find.text('Pendiente'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay amenidades configuradas', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response('[]', 200);
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);

    expect(find.text('Todavía no hay amenidades configuradas.'), findsOneWidget);
  });

  testWidgets('muestra un mensaje cuando no hay reservaciones propias', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(_fixtureAmenidades, 200);
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);

    expect(find.text('Todavía no tienes reservaciones.'), findsOneWidget);
  });

  testWidgets('el botón de solicitar queda deshabilitado sin fechas elegidas', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(_fixtureAmenidades, 200);
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);

    final boton = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Solicitar'));
    expect(boton.onPressed, isNull);
  });
}
