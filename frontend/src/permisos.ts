import type { Rol } from './types'

/**
 * Qué secciones del panel puede usar cada rol. Es la ÚNICA fuente de verdad para el menú, para el bloqueo de
 * direcciones escritas a mano y para la página de inicio de cada rol; las pantallas derivan de aquí su propia
 * comprobación (`rolesDe`), así que no pueden contradecirse.
 *
 * Se decidió con lo que el backend realmente permite (guardas de rol de cada endpoint) y con lo que cada pantalla
 * necesita para cargar completa: una sección solo aparece si el rol puede usar lo que la pantalla pide. El backend
 * sigue siendo quien autoriza; esto evita mostrar caminos que terminarían en «sin acceso».
 */
export interface Seccion {
  ruta: string
  etiqueta: string
  roles: readonly Rol[]
}

// El orden es el del menú.
export const SECCIONES: readonly Seccion[] = [
  { ruta: '/properties', etiqueta: 'Viviendas', roles: ['admin', 'tesorero'] },
  { ruta: '/users', etiqueta: 'Usuarios', roles: ['admin'] },
  { ruta: '/organizacion', etiqueta: 'Organización', roles: ['admin'] },
  { ruta: '/fees', etiqueta: 'Cuotas', roles: ['admin', 'tesorero'] },
  { ruta: '/collection', etiqueta: 'Cobranza', roles: ['admin', 'tesorero'] },
  { ruta: '/payment-proofs', etiqueta: 'Comprobantes', roles: ['admin', 'tesorero'] },
  { ruta: '/payment-agreements', etiqueta: 'Acuerdos', roles: ['admin', 'tesorero', 'comite_aprobador', 'comite_lectura'] },
  { ruta: '/clabe', etiqueta: 'CLABE', roles: ['admin'] },
  { ruta: '/dashboard', etiqueta: 'Dashboard', roles: ['admin', 'tesorero'] },
  { ruta: '/expenses', etiqueta: 'Gastos', roles: ['admin', 'tesorero', 'comite_aprobador', 'comite_lectura'] },
  { ruta: '/reports/export', etiqueta: 'Exportar', roles: ['admin', 'tesorero'] },
  { ruta: '/amenities', etiqueta: 'Amenidades', roles: ['admin'] },
  { ruta: '/reservations', etiqueta: 'Reservaciones', roles: ['admin', 'tesorero', 'comite_aprobador'] },
  { ruta: '/security', etiqueta: 'Seguridad', roles: ['admin', 'guardia', 'comite_aprobador', 'comite_lectura'] },
  { ruta: '/announcements', etiqueta: 'Avisos', roles: ['admin'] },
  { ruta: '/announcement-questions', etiqueta: 'Dudas', roles: ['admin', 'comite_aprobador', 'comite_lectura'] },
  { ruta: '/reglamento', etiqueta: 'Reglamento', roles: ['admin', 'tesorero', 'comite_aprobador', 'comite_lectura'] },
]

// Primera pantalla de cada rol al entrar (la que más usa). Sin entrada: la primera sección que pueda ver.
const INICIO: Partial<Record<Rol, string>> = {
  admin: '/properties',
  tesorero: '/collection',
  comite_aprobador: '/payment-agreements',
  comite_lectura: '/payment-agreements',
  guardia: '/security',
}

export function rolesDe(ruta: string): readonly Rol[] {
  return SECCIONES.find((s) => s.ruta === ruta)?.roles ?? []
}

export function seccionesDe(rol: string | undefined): Seccion[] {
  return SECCIONES.filter((s) => (s.roles as readonly string[]).includes(rol ?? ''))
}

/** La sección a la que pertenece una dirección (`/properties/abc` es de `/properties`), o undefined si no es de ninguna. */
export function seccionDe(pathname: string): Seccion | undefined {
  return SECCIONES.find((s) => pathname === s.ruta || pathname.startsWith(`${s.ruta}/`))
}

export function puedeVer(rol: string | undefined, pathname: string): boolean {
  const seccion = seccionDe(pathname)
  return seccion !== undefined && (seccion.roles as readonly string[]).includes(rol ?? '')
}

/** Adónde llevar a un rol al entrar o si escribe una dirección que no le corresponde; null si no tiene secciones. */
export function inicioDe(rol: string | undefined): string | null {
  const propio = INICIO[rol as Rol]
  if (propio !== undefined) return propio
  return seccionesDe(rol)[0]?.ruta ?? null
}
