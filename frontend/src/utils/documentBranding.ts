// Pestaña del navegador: el nombre y el logo del condominio no son solo de la barra lateral — quien tiene varias
// pestañas abiertas (o varios condominios) necesita distinguirlas ahí también.
const TITULO_BASE = 'Vivecom'
const FAVICON_POR_DEFECTO = '/favicon.svg'

export function aplicarTituloDelDocumento(nombreCondominio: string): void {
  document.title = nombreCondominio ? `${nombreCondominio} — ${TITULO_BASE}` : TITULO_BASE
}

export function aplicarFaviconDelDocumento(url: string | null): void {
  const enlace = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (!enlace) return
  enlace.href = url ?? FAVICON_POR_DEFECTO
}

export function restablecerBrandingDelDocumento(): void {
  document.title = TITULO_BASE
  aplicarFaviconDelDocumento(null)
}
