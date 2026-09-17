// El backend guarda y regresa datetimes como UTC "naive" (sin sufijo de
// zona horaria). DateTime.parse de Dart interpreta un ISO string SIN sufijo
// de zona como hora LOCAL del dispositivo, no UTC — hay que ser explícito o
// las horas salen corridas por el offset de zona del usuario (mismo bug real
// encontrado en F1-33/mobile y F2-19/mobile).

DateTime utcNaiveToDateTime(String fechaNaiveUtc) {
  return DateTime.parse(fechaNaiveUtc.endsWith('Z') ? fechaNaiveUtc : '${fechaNaiveUtc}Z');
}

String _pad(int n) => n.toString().padLeft(2, '0');

// Formatea en hora LOCAL del dispositivo — llamar con un DateTime ya
// convertido vía utcNaiveToDateTime().
String formatoHoraCorta(DateTime fecha) {
  final local = fecha.toLocal();
  return '${_pad(local.hour)}:${_pad(local.minute)}';
}
