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

  const amenidadConReglas = '''
[{"id": "a1", "nombre": "Área adoquinada", "periodo_limite_horas": 48, "capacidad": 1, "cuota": 1000.0,
  "notas_reglamento": "Reglamento Art. 2",
  "reglas": ["Solicítala con al menos 8 días de anticipación.", "Horario máximo de uso: hasta las 01:00.",
             "Cuota de uso: \$1,000.00 MXN, se entrega a tesorería al solicitarla."]}]
''';

  testWidgets('muestra las reglas de uso de la amenidad seleccionada', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(amenidadConReglas, 200);
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);

    final reglas = find.byKey(const Key('reglas_amenidad'));
    expect(reglas, findsOneWidget);
    expect(
      find.descendant(of: reglas, matching: find.text('• Solicítala con al menos 8 días de anticipación.')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: reglas, matching: find.text('• Horario máximo de uso: hasta las 01:00.')),
      findsOneWidget,
    );
    expect(find.descendant(of: reglas, matching: find.text('Reglamento Art. 2')), findsOneWidget);
  });

  testWidgets('una amenidad sin reglas no muestra el recuadro de reglas', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(_fixtureAmenidades, 200);
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);

    expect(find.byKey(const Key('reglas_amenidad')), findsNothing);
  });

  testWidgets('cada reservación con cuota dice si tesorería ya la recibió', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(amenidadConReglas, 200);
      return http.Response('''
[{"id": "r1", "amenity_id": "a1", "property_id": "p1", "fecha_inicio": "2026-10-01T10:00:00",
  "fecha_fin": "2026-10-01T12:00:00", "estado": "aprobada", "aprobador_id": null, "cuota": 1000.0, "cuota_pagada": false},
 {"id": "r2", "amenity_id": "a1", "property_id": "p1", "fecha_inicio": "2026-11-01T10:00:00",
  "fecha_fin": "2026-11-01T12:00:00", "estado": "aprobada", "aprobador_id": null, "cuota": 1000.0, "cuota_pagada": true}]
''', 200);
    });

    await pumpReservaciones(tester, mockClient);

    expect(find.textContaining('pendiente de entregar a tesorería'), findsOneWidget);
    expect(find.textContaining('recibida por tesorería'), findsOneWidget);
  });

  testWidgets('sin cuota, la reservación muestra solo su estado', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(_fixtureAmenidades, 200);
      return http.Response(_fixtureReservaciones, 200);
    });

    await pumpReservaciones(tester, mockClient);

    expect(find.textContaining('tesorería'), findsNothing);
  });

  testWidgets('al elegir el día de inicio se muestran los lugares libres y lo ya reservado', (tester) async {
    String? fechaConsultada;
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(amenidadConReglas, 200);
      if (request.url.path == '/amenities/a1/disponibilidad') {
        fechaConsultada = request.url.queryParameters['fecha'];
        return http.Response(
          '{"amenity_id": "a1", "fecha": "$fechaConsultada", "capacidad": 1, "cupos_libres_todo_el_dia": 0, '
          '"reservaciones": [{"fecha_inicio": "2026-10-05T16:00:00", "fecha_fin": "2026-10-05T20:00:00"}], "reglas": []}',
          200,
        );
      }
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);
    await tester.tap(find.text('Inicio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK')); // fecha (hoy, por defecto)
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK')); // hora
    await tester.pumpAndSettle();

    expect(fechaConsultada, isNotNull);
    final bloque = find.byKey(const Key('disponibilidad_dia'));
    expect(bloque, findsOneWidget);
    expect(
      find.descendant(of: bloque, matching: find.textContaining('0 de 1 lugar libre todo el día')),
      findsOneWidget,
    );
    expect(find.descendant(of: bloque, matching: find.text('Ya reservado:')), findsOneWidget);
  });

  testWidgets('si la disponibilidad falla, no se muestra pero se puede seguir solicitando', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/amenities') return http.Response(amenidadConReglas, 200);
      if (request.url.path.endsWith('/disponibilidad')) return http.Response('{"detail": "x"}', 500);
      return http.Response('[]', 200);
    });

    await pumpReservaciones(tester, mockClient);
    await tester.tap(find.text('Inicio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('disponibilidad_dia')), findsNothing);
    expect(find.text('Solicitar'), findsOneWidget);
  });
}
