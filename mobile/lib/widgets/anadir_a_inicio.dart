import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../utils/app_instalada.dart';

/// Solo tiene sentido en la web abierta desde un iPhone/iPad que todavía no la tiene en la pantalla de inicio.
bool debeOfrecerAtajo({required bool esWeb, required TargetPlatform plataforma, required bool instalada}) =>
    esWeb && plataforma == TargetPlatform.iOS && !instalada;

const pasosDelAtajo = [
  'Abre esta página en Safari.',
  'Toca el botón Compartir (el cuadrado con la flecha hacia arriba), en la barra de abajo.',
  'Baja en el menú y elige «Añadir a pantalla de inicio».',
  'Toca «Añadir». Vivecom aparecerá como una app más en tu pantalla.',
];

/// Tarjeta «Ponla en tu pantalla de inicio». Apple NO permite que una página añada el atajo por sí sola (no existe un
/// botón que lo haga): lo único posible es guiar los pasos, así que el botón abre una guía.
class AnadirAPantallaDeInicio extends StatelessWidget {
  final bool? visible; // null = decidir según la plataforma y si ya está instalada

  const AnadirAPantallaDeInicio({super.key, this.visible});

  void _mostrarGuia(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (dialogo) => AlertDialog(
        key: const Key('guia_atajo'),
        title: const Text('Ponla en tu pantalla de inicio'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < pasosDelAtajo.length; i++)
              Padding(padding: const EdgeInsets.only(bottom: 8), child: Text('${i + 1}. ${pasosDelAtajo[i]}')),
          ],
        ),
        actions: [TextButton(onPressed: () => Navigator.of(dialogo).pop(), child: const Text('Entendido'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final mostrar =
        visible ?? debeOfrecerAtajo(esWeb: kIsWeb, plataforma: defaultTargetPlatform, instalada: appInstalada());
    if (!mostrar) return const SizedBox.shrink();
    return Card(
      key: const Key('tarjeta_atajo'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('¿Usas iPhone?', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Añade Vivecom a tu pantalla de inicio y ábrela como cualquier app, sin el navegador.'),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              key: const Key('anadir_a_inicio'),
              onPressed: () => _mostrarGuia(context),
              icon: const Icon(Icons.add_to_home_screen),
              label: const Text('Añadir a la pantalla de inicio'),
            ),
          ],
        ),
      ),
    );
  }
}
