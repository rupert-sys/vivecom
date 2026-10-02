import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Layout } from './Layout'
import * as tenantApi from '../api/tenant'
import { useAuth } from '../auth/AuthContext'
import { SECCIONES } from '../permisos'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

vi.spyOn(tenantApi, 'getTenantConfig').mockResolvedValue({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: false })
vi.spyOn(tenantApi, 'fetchLogoObjectUrl').mockResolvedValue(null)

function mockUser(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { sub: 'u1', tenant_id: 't1', schema: 's1', rol, property_id: null, exp: 0 },
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function renderEn(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route element={<Layout />}>
          {SECCIONES.map((s) => (
            <Route key={s.ruta} path={`${s.ruta}/*`} element={<p>Contenido de {s.etiqueta}</p>} />
          ))}
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

const menu = () =>
  within(screen.getByRole('navigation', { name: 'Secciones del panel' })).queryAllByRole('link').map((a) => a.textContent)

describe('Layout: el menú muestra solo lo que el rol puede usar', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('el administrador ve las 17 secciones', () => {
    mockUser('admin')
    renderEn('/properties')
    expect(menu()).toHaveLength(SECCIONES.length)
    expect(menu()).toContain('Usuarios')
  })

  it('tesorería no ve Usuarios, CLABE, Avisos, Amenidades, Seguridad ni Dudas', () => {
    mockUser('tesorero')
    renderEn('/collection')
    expect(menu()).toEqual([
      'Dashboard', 'Viviendas', 'Cuotas', 'Cobranza', 'Comprobantes', 'Acuerdos', 'Gastos', 'Caja chica/grande', 'Exportar',
      'Reservaciones', 'Reglamento',
    ])
  })

  it('el comité aprobador ve solo lo suyo', () => {
    mockUser('comite_aprobador')
    renderEn('/payment-agreements')
    expect(menu()).toEqual(['Acuerdos', 'Gastos', 'Caja chica/grande', 'Reservaciones', 'Seguridad', 'Dudas', 'Reglamento'])
  })

  it('el comité de solo lectura no ve Reservaciones', () => {
    mockUser('comite_lectura')
    renderEn('/payment-agreements')
    expect(menu()).toEqual(['Acuerdos', 'Gastos', 'Caja chica/grande', 'Seguridad', 'Dudas', 'Reglamento'])
  })

  it('escribir a mano la dirección de una sección ajena lleva al inicio del rol, sin mostrar su contenido', () => {
    mockUser('tesorero')
    renderEn('/users')
    expect(screen.queryByText('Contenido de Usuarios')).not.toBeInTheDocument()
    expect(screen.getByText('Contenido de Dashboard')).toBeInTheDocument()
  })

  it('una dirección con parámetros de una sección permitida sí se muestra', () => {
    mockUser('tesorero')
    renderEn('/properties/abc-123')
    expect(screen.getByText('Contenido de Viviendas')).toBeInTheDocument()
  })

  it('el comité no entra a Viviendas ni a Cobranza aunque escriba la dirección', () => {
    mockUser('comite_lectura')
    renderEn('/collection')
    expect(screen.queryByText('Contenido de Cobranza')).not.toBeInTheDocument()
    expect(screen.getByText('Contenido de Acuerdos')).toBeInTheDocument()
  })

  it('un rol sin secciones (residente) ve un aviso y ningún menú', () => {
    mockUser('residente')
    renderEn('/properties')
    expect(screen.getByText(/no tiene secciones en el panel/i)).toBeInTheDocument()
    expect(menu()).toEqual([])
  })
})

describe('Layout: el nombre y el logo del condominio también se aplican a la pestaña del navegador', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockUser('admin')
    document.title = 'algo previo'
    document.head.querySelectorAll('link[rel="icon"]').forEach((n) => n.remove())
    const link = document.createElement('link')
    link.rel = 'icon'
    link.href = '/favicon.svg'
    document.head.appendChild(link)
    // jsdom no implementa URL.revokeObjectURL: Layout la llama al desmontar para liberar el object URL del logo.
    // No se limpia en un afterEach propio: correría antes del desmontar automático de Testing Library (los
    // afterEach anidados corren primero) y fallaría igual; el siguiente beforeEach ya vuelve a fijar el stub.
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:stub'), revokeObjectURL: vi.fn() })
  })

  function favicon() {
    return document.querySelector('link[rel="icon"]')?.getAttribute('href')
  }

  it('el título de la pestaña toma el nombre del condominio', async () => {
    vi.spyOn(tenantApi, 'getTenantConfig').mockResolvedValue({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: false })
    vi.spyOn(tenantApi, 'fetchLogoObjectUrl').mockResolvedValue(null)

    renderEn('/properties')

    // El nombre del condominio aparece tanto en la barra lateral como en la
    // barra superior móvil: con findAllByText basta esperar a que cargue.
    await screen.findAllByText('Residencial Las Torres')
    expect(document.title).toBe('Residencial Las Torres — Vivecom')
    expect(favicon()).toBe('/favicon.svg') // sin logo, se queda el de Vivecom
  })

  it('con logo, también se vuelve el favicon de la pestaña', async () => {
    vi.spyOn(tenantApi, 'getTenantConfig').mockResolvedValue({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: true })
    vi.spyOn(tenantApi, 'fetchLogoObjectUrl').mockResolvedValue('blob:logo-del-condominio')

    renderEn('/properties')

    await screen.findAllByText('Residencial Las Torres')
    expect(favicon()).toBe('blob:logo-del-condominio')
  })

  it('al salir del panel, la pestaña vuelve a su título y favicon genéricos', async () => {
    vi.spyOn(tenantApi, 'getTenantConfig').mockResolvedValue({ id: 't1', nombre: 'Residencial Las Torres', tiene_logo: true })
    vi.spyOn(tenantApi, 'fetchLogoObjectUrl').mockResolvedValue('blob:logo-del-condominio')

    const { unmount } = renderEn('/properties')
    await screen.findAllByText('Residencial Las Torres')

    unmount()

    expect(document.title).toBe('Vivecom')
    expect(favicon()).toBe('/favicon.svg')
  })
})
