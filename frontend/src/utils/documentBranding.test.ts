import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  aplicarFaviconDelDocumento,
  aplicarTituloDelDocumento,
  restablecerBrandingDelDocumento,
} from './documentBranding'

describe('documentBranding', () => {
  beforeEach(() => {
    document.title = 'algo previo'
    document.head.querySelectorAll('link[rel="icon"]').forEach((n) => n.remove())
    const link = document.createElement('link')
    link.rel = 'icon'
    link.href = '/favicon.svg'
    document.head.appendChild(link)
  })

  afterEach(() => {
    document.title = ''
  })

  it('el título de la pestaña incluye el nombre del condominio', () => {
    aplicarTituloDelDocumento('Residencial Las Torres')
    expect(document.title).toBe('Residencial Las Torres — Vivecom')
  })

  it('sin nombre, el título se queda genérico', () => {
    aplicarTituloDelDocumento('')
    expect(document.title).toBe('Vivecom')
  })

  it('el favicon cambia a la URL dada', () => {
    aplicarFaviconDelDocumento('blob:logo-del-condominio')
    expect(document.querySelector('link[rel="icon"]')?.getAttribute('href')).toBe('blob:logo-del-condominio')
  })

  it('sin logo (null), el favicon vuelve al de Vivecom', () => {
    aplicarFaviconDelDocumento('blob:algo')
    aplicarFaviconDelDocumento(null)
    expect(document.querySelector('link[rel="icon"]')?.getAttribute('href')).toBe('/favicon.svg')
  })

  it('restablecer regresa el título y el favicon a los genéricos', () => {
    aplicarTituloDelDocumento('Residencial Las Torres')
    aplicarFaviconDelDocumento('blob:logo')

    restablecerBrandingDelDocumento()

    expect(document.title).toBe('Vivecom')
    expect(document.querySelector('link[rel="icon"]')?.getAttribute('href')).toBe('/favicon.svg')
  })
})
