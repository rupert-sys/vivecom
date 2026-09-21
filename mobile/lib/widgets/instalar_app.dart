import 'package:flutter/material.dart';

import 'anadir_a_inicio.dart';
import 'descarga_apk.dart';

/// Lo que se ofrece para «tener la app» según el aparato desde el que se abre la versión web: en Android, bajar el
/// APK; en iPhone, añadirla a la pantalla de inicio. En cualquier otro caso (app nativa, computadora), nada.
class InstalarApp extends StatelessWidget {
  final Widget apk;
  final Widget atajo;

  const InstalarApp({super.key, this.apk = const DescargarApk(), this.atajo = const AnadirAPantallaDeInicio()});

  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [apk, atajo]);
}
