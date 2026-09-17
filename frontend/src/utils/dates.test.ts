import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { dateToDatetimeLocalValue, datetimeLocalValueToUtcIso, utcNaiveToDate } from './dates'

describe('utcNaiveToDate', () => {
  // El contenedor de Docker donde corre esta suite normalmente ya está en
  // UTC — bajo esa zona, "naive interpretado como local" y "naive
  // interpretado como UTC" dan el MISMO resultado por coincidencia, lo que
  // ocultaría una regresión que quitara el forzado de 'Z'. Se fuerza una
  // zona horaria explícita y distinta (México, UTC-6) para que la prueba
  // de verdad distinga el comportamiento correcto del bug real que se
  // encontró en el navegador.
  const TZ_ORIGINAL = process.env.TZ

  beforeEach(() => {
    process.env.TZ = 'America/Mexico_City'
  })

  afterEach(() => {
    process.env.TZ = TZ_ORIGINAL
  })

  it('interpreta un string naive del backend como UTC, no como hora local del navegador', () => {
    // Bug real: sin forzar 'Z', "2026-09-17T04:33:27" (naive-UTC del
    // backend, un aviso publicado hace un instante) se interpretaba como
    // las 4:33am hora de México — 6 horas DESPUÉS del instante real en
    // UTC — así que un aviso recién publicado aparecía como "Programado".
    const resultado = utcNaiveToDate('2026-09-17T04:33:27')
    const esperado = new Date('2026-09-17T04:33:27Z')
    expect(resultado.getTime()).toBe(esperado.getTime())
    // Si el bug estuviera de vuelta (sin agregar 'Z'), el resultado
    // quedaría 6 horas adelantado respecto al instante real en UTC.
    expect(resultado.getTime()).not.toBe(new Date('2026-09-17T04:33:27').getTime())
  })

  it('no duplica la Z si el string ya la trae', () => {
    const resultado = utcNaiveToDate('2026-09-17T04:33:27Z')
    expect(resultado.getTime()).toBe(new Date('2026-09-17T04:33:27Z').getTime())
  })
})

describe('dateToDatetimeLocalValue / datetimeLocalValueToUtcIso', () => {
  it('ida y vuelta: un valor de datetime-local sobrevive el round-trip a UTC ISO y de regreso', () => {
    const valorOriginal = '2026-09-20T10:30'
    const isoUtc = datetimeLocalValueToUtcIso(valorOriginal)
    // El ISO resultante debe ser interpretable de vuelta al mismo instante.
    const deVuelta = dateToDatetimeLocalValue(new Date(isoUtc))
    expect(deVuelta).toBe(valorOriginal)
  })
})
