import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// El APK que deploy/ sirve junto a la app web (deploy/scripts/build-apk.sh lo deja con este nombre).
const nombreApk = 'vivecom-android.apk';

/// Solo tiene sentido ofrecer el APK a quien abre la app WEB desde un Android: en un iPhone no sirve, y quien ya tiene
/// la app instalada (o la abre en una computadora) no lo necesita.
bool debeOfrecerApk({required bool esWeb, required TargetPlatform plataforma}) =>
    esWeb && plataforma == TargetPlatform.android;

/// El APK, en la raíz del mismo sitio desde el que se abrió la app (sea cual sea la ruta actual).
Uri urlDelApk() => Uri.base.resolve('/$nombreApk');

typedef AbrirEnlace = Future<void> Function(Uri url);

// Misma pestaña: el navegador ve un archivo y lo descarga sin dejar una pestaña en blanco.
Future<void> abrirEnLaMismaPestana(Uri url) => launchUrl(url, webOnlyWindowName: '_self');

/// Tarjeta «¿Usas Android? Instala la app». Inyectable (visible, abrir) para probarla sin plataforma real.
class DescargarApk extends StatelessWidget {
  final bool? visible; // null = decidir según la plataforma
  final AbrirEnlace abrir;

  const DescargarApk({super.key, this.visible, this.abrir = abrirEnLaMismaPestana});

  @override
  Widget build(BuildContext context) {
    final mostrar = visible ?? debeOfrecerApk(esWeb: kIsWeb, plataforma: defaultTargetPlatform);
    if (!mostrar) return const SizedBox.shrink();
    return Card(
      key: const Key('tarjeta_apk'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('¿Usas Android?', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
              'Instala la app de Vivecom en tu teléfono: se abre más rápido y funciona mejor que desde el navegador.',
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              key: const Key('descargar_apk'),
              onPressed: () => abrir(urlDelApk()),
              icon: const Icon(Icons.android),
              label: const Text('Descargar app para Android'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Al abrir el archivo, Android te pedirá permitir instalar apps de esta fuente y Play Protect puede avisar '
              'porque no viene de la tienda: elige «Instalar de todos modos».',
              key: Key('ayuda_apk'),
              style: TextStyle(fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
