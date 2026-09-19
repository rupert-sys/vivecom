import { describe, expect, it } from 'vitest'
import { formatoPorcentaje } from './reglamento'

describe('formatoPorcentaje', () => {
  it('muestra la fracción como porcentaje sin ceros de sobra', () => {
    expect(formatoPorcentaje(0.1)).toBe('10%')
    expect(formatoPorcentaje(0.05)).toBe('5%')
    expect(formatoPorcentaje(0.025)).toBe('2.5%')
    expect(formatoPorcentaje(0)).toBe('0%')
  })

  it('no arrastra el error de coma flotante', () => {
    expect(formatoPorcentaje(0.07)).toBe('7%')
  })
})
