import { describe, expect, it } from 'vitest'
import { SECCIONES, inicioDe, puedeVer, rolesDe, seccionDe, seccionesDe } from './permisos'

const etiquetas = (rol: string) => seccionesDe(rol).map((s) => s.etiqueta)

describe('permisos del panel', () => {
  it('el administrador ve todas las secciones', () => {
    expect(seccionesDe('admin')).toHaveLength(SECCIONES.length)
  })

  it('tesorería solo ve lo de cobranza y finanzas', () => {
    expect(etiquetas('tesorero')).toEqual([
      'Dashboard', 'Viviendas', 'Cuotas', 'Cobranza', 'Comprobantes', 'Acuerdos', 'Gastos', 'Exportar', 'Reservaciones', 'Reglamento',
    ])
  })

  it('el comité aprobador ve lo que decide; el de solo lectura, lo mismo salvo reservaciones', () => {
    expect(etiquetas('comite_aprobador')).toEqual(['Acuerdos', 'Gastos', 'Reservaciones', 'Seguridad', 'Dudas', 'Reglamento'])
    expect(etiquetas('comite_lectura')).toEqual(['Acuerdos', 'Gastos', 'Seguridad', 'Dudas', 'Reglamento'])
  })

  it('ni tesorería ni el comité ven la gestión de usuarios, la CLABE, los avisos ni las amenidades', () => {
    for (const rol of ['tesorero', 'comite_aprobador', 'comite_lectura']) {
      for (const ruta of ['/users', '/clabe', '/announcements', '/amenities']) {
        expect(puedeVer(rol, ruta), `${rol} ${ruta}`).toBe(false)
      }
    }
  })

  it('el guardia solo ve Seguridad; los residentes y voceros no tienen secciones en el panel', () => {
    expect(etiquetas('guardia')).toEqual(['Seguridad'])
    expect(seccionesDe('residente')).toEqual([])
    expect(seccionesDe('vocero')).toEqual([])
    expect(seccionesDe(undefined)).toEqual([])
  })

  it('una dirección con parámetros pertenece a su sección', () => {
    expect(seccionDe('/properties/abc-123')?.ruta).toBe('/properties')
    expect(puedeVer('tesorero', '/properties/abc-123')).toBe(true)
    expect(puedeVer('comite_lectura', '/properties/abc-123')).toBe(false)
    expect(seccionDe('/properties-otra')).toBeUndefined() // no se confunde con un prefijo parecido
    expect(seccionDe('/no-existe')).toBeUndefined()
    expect(puedeVer('admin', '/no-existe')).toBe(false)
  })

  it('cada rol entra a la pantalla que más usa, y esa pantalla es una que puede ver', () => {
    expect(inicioDe('admin')).toBe('/dashboard')
    expect(inicioDe('tesorero')).toBe('/dashboard')
    expect(inicioDe('comite_aprobador')).toBe('/payment-agreements')
    expect(inicioDe('comite_lectura')).toBe('/payment-agreements')
    expect(inicioDe('guardia')).toBe('/security')
    expect(inicioDe('residente')).toBeNull()
    for (const rol of ['admin', 'tesorero', 'comite_aprobador', 'comite_lectura', 'guardia']) {
      expect(puedeVer(rol, inicioDe(rol)!), `inicio de ${rol}`).toBe(true)
    }
  })

  it('cada ruta aparece una sola vez y rolesDe devuelve sus roles', () => {
    const rutas = SECCIONES.map((s) => s.ruta)
    expect(new Set(rutas).size).toBe(rutas.length)
    expect(rolesDe('/collection')).toEqual(['admin', 'tesorero'])
    expect(rolesDe('/no-existe')).toEqual([])
  })
})
