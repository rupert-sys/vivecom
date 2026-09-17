// El backend guarda y regresa datetimes como UTC "naive" (sin sufijo de
// zona horaria — convención de todo el proyecto, ver core/database.py del
// backend). El constructor Date de JavaScript interpreta un ISO string SIN
// sufijo de zona como hora LOCAL del navegador, no UTC — así que hay que
// ser explícito en ambas direcciones o las comparaciones/despliegues salen
// corridos por el offset de la zona horaria del usuario.

export function utcNaiveToDate(fechaNaiveUtc: string): Date {
  return new Date(fechaNaiveUtc.endsWith('Z') ? fechaNaiveUtc : `${fechaNaiveUtc}Z`)
}

// Para poblar un <input type="datetime-local">, que siempre opera en hora
// local del navegador (no soporta zona horaria explícita).
export function dateToDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

// El valor de un <input type="datetime-local"> (ej. "2026-09-20T10:30") se
// interpreta como hora LOCAL al pasarlo a `new Date()` — toISOString() lo
// convierte a UTC con sufijo 'Z', que el backend sabe interpretar
// correctamente (ver _a_naive_utc() en announcements.py).
export function datetimeLocalValueToUtcIso(valor: string): string {
  return new Date(valor).toISOString()
}
