import 'package:app_residente/widgets/oculta_teclado.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget app({VoidCallback? alPulsar}) => MaterialApp(
    builder: (context, child) => OcultaTecladoAlTocarFuera(child: child),
    home: Scaffold(
      body: Column(
        children: [
          const TextField(key: Key('monto'), keyboardType: TextInputType.numberWithOptions(decimal: true)),
          const TextField(key: Key('causa'), maxLines: 4),
          ElevatedButton(key: const Key('boton'), onPressed: alPulsar ?? () {}, child: const Text('Enviar')),
          const Expanded(
            child: ColoredBox(key: Key('vacio'), color: Colors.white),
          ),
        ],
      ),
    ),
  );

  bool tecladoAbierto(WidgetTester tester) => tester.testTextInput.isVisible;

  testWidgets('tocar un área vacía esconde el teclado de un campo numérico', (tester) async {
    await tester.pumpWidget(app());
    await tester.showKeyboard(find.byKey(const Key('monto')));
    expect(tecladoAbierto(tester), isTrue);

    await tester.tapAt(tester.getCenter(find.byKey(const Key('vacio')))); // área sin nada que atienda el toque
    await tester.pump();

    expect(tecladoAbierto(tester), isFalse);
  });

  testWidgets('también esconde el de un campo de varias líneas, que no tiene tecla Listo', (tester) async {
    await tester.pumpWidget(app());
    await tester.showKeyboard(find.byKey(const Key('causa')));
    expect(tecladoAbierto(tester), isTrue);

    await tester.tapAt(tester.getCenter(find.byKey(const Key('vacio')))); // área sin nada que atienda el toque
    await tester.pump();

    expect(tecladoAbierto(tester), isFalse);
  });

  testWidgets('tocar otro campo NO esconde el teclado: el foco pasa al nuevo campo', (tester) async {
    await tester.pumpWidget(app());
    await tester.showKeyboard(find.byKey(const Key('monto')));

    await tester.tap(find.byKey(const Key('causa')));
    await tester.pump();

    expect(tecladoAbierto(tester), isTrue);
  });

  testWidgets('un botón sigue funcionando: el toque no se lo lleva el gesto de fondo', (tester) async {
    var pulsado = 0;
    await tester.pumpWidget(app(alPulsar: () => pulsado++));
    await tester.showKeyboard(find.byKey(const Key('monto')));

    await tester.tap(find.byKey(const Key('boton')));
    await tester.pump();

    expect(pulsado, 1);
  });
}
