import 'package:flutter/material.dart';

/// Tocar fuera de un campo de texto le quita el foco y esconde el teclado.
///
/// En iOS el teclado numérico y los campos de varias líneas no tienen tecla «Listo» (el retorno solo mete un
/// salto de línea), así que sin esto el teclado no se puede esconder. Un botón o el propio campo ganan el toque:
/// solo dispara con un toque en un área sin nada que lo atienda.
class OcultaTecladoAlTocarFuera extends StatelessWidget {
  final Widget? child;
  const OcultaTecladoAlTocarFuera({super.key, this.child});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onTap: () => FocusManager.instance.primaryFocus?.unfocus(),
      child: child,
    );
  }
}
