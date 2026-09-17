// El backend guarda y regresa datetimes como UTC "naive" (sin sufijo de
// zona horaria — misma convención documentada en el frontend web,
// frontend/src/utils/dates.ts). DateTime.parse de Dart interpreta un ISO
// string SIN sufijo de zona como hora LOCAL del dispositivo, no UTC — hay
// que ser explícito o los despliegues salen corridos por el offset de la
// zona horaria del usuario (mismo bug real encontrado en F1-33).

DateTime utcNaiveToDateTime(String fechaNaiveUtc) {
  return DateTime.parse(fechaNaiveUtc.endsWith('Z') ? fechaNaiveUtc : '${fechaNaiveUtc}Z');
}
