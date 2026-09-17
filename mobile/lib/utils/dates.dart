// El backend guarda y regresa datetimes como UTC "naive" (sin sufijo de
// zona horaria — misma convención documentada en el frontend web,
// frontend/src/utils/dates.ts). DateTime.parse de Dart interpreta un ISO
// string SIN sufijo de zona como hora LOCAL del dispositivo, no UTC — hay
// que ser explícito o los despliegues salen corridos por el offset de la
// zona horaria del usuario (mismo bug real encontrado en F1-33).

DateTime utcNaiveToDateTime(String fechaNaiveUtc) {
  return DateTime.parse(fechaNaiveUtc.endsWith('Z') ? fechaNaiveUtc : '${fechaNaiveUtc}Z');
}

String _pad(int n) => n.toString().padLeft(2, '0');

// Formatea en hora LOCAL del dispositivo — llamar con un DateTime ya
// convertido vía utcNaiveToDateTime().toLocal() si viene del backend.
String formatoFechaCorta(DateTime fecha) {
  final local = fecha.toLocal();
  return '${local.year}-${_pad(local.month)}-${_pad(local.day)}';
}
