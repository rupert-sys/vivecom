import 'package:app_residente/widgets/anadir_a_inicio.dart';
import 'package:app_residente/widgets/descarga_apk.dart';
import 'package:app_residente/widgets/instalar_app.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('el atajo solo se ofrece en la web de un iPhone que aún no la tiene en la pantalla de inicio', () {
    expect(debeOfrecerAtajo(esWeb: true, plataforma: TargetPlatform.iOS, instalada: false), isTrue);
    expect(
      debeOfrecerAtajo(esWeb: true, plataforma: TargetPlatform.iOS, instalada: true),
      isFalse,
    ); // ya la abrió desde el ícono
    expect(debeOfrecerAtajo(esWeb: true, plataforma: TargetPlatform.android, instalada: false), isFalse);
    expect(debeOfrecerAtajo(esWeb: false, plataforma: TargetPlatform.iOS, instalada: false), isFalse); // app nativa
  });

  testWidgets('visible: el botón abre la guía con los pasos y se puede cerrar', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: AnadirAPantallaDeInicio(visible: true))));

    expect(find.text('¿Usas iPhone?'), findsOneWidget);
    await tester.tap(find.byKey(const Key('anadir_a_inicio')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('guia_atajo')), findsOneWidget);
    for (var i = 0; i < pasosDelAtajo.length; i++) {
      expect(find.text('${i + 1}. ${pasosDelAtajo[i]}'), findsOneWidget);
    }
    expect(find.textContaining('Añadir a pantalla de inicio'), findsWidgets);

    await tester.tap(find.text('Entendido'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('guia_atajo')), findsNothing);
  });

  testWidgets('no visible, y sin forzarlo en la app nativa o en las pruebas, no muestra nada', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: AnadirAPantallaDeInicio(visible: false))));
    expect(find.byKey(const Key('tarjeta_atajo')), findsNothing);

    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: AnadirAPantallaDeInicio())));
    expect(find.byKey(const Key('tarjeta_atajo')), findsNothing);
  });

  testWidgets('InstalarApp junta las dos ofertas y cada una decide por su cuenta', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: InstalarApp(apk: DescargarApk(visible: true), atajo: AnadirAPantallaDeInicio(visible: true)),
        ),
      ),
    );
    expect(find.byKey(const Key('descargar_apk')), findsOneWidget);
    expect(find.byKey(const Key('anadir_a_inicio')), findsOneWidget);

    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: InstalarApp())));
    expect(find.byKey(const Key('descargar_apk')), findsNothing);
    expect(find.byKey(const Key('anadir_a_inicio')), findsNothing);
  });
}
