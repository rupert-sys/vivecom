import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Layout } from './Layout'
import { useAuth } from '../auth/AuthContext'
import { SECCIONES } from '../permisos'

vi.mock('../auth/AuthContext', () => ({ useAuth: vi.fn() }))

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

const menu = () => within(screen.getByRole('navigation')).queryAllByRole('link').map((a) => a.textContent)

describe('Layout: el menú muestra solo lo que el rol puede usar', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('el administrador ve las 16 secciones', () => {
    mockUser('admin')
    renderEn('/properties')
    expect(menu()).toHaveLength(SECCIONES.length)
    expect(menu()).toContain('Usuarios')
  })

  it('tesorería no ve Usuarios, CLABE, Avisos, Amenidades, Seguridad ni Dudas', () => {
    mockUser('tesorero')
    renderEn('/collection')
    expect(menu()).toEqual(['Viviendas', 'Cuotas', 'Cobranza', 'Comprobantes', 'Acuerdos', 'Dashboard', 'Gastos', 'Exportar', 'Reservaciones', 'Reglamento'])
  })

  it('el comité aprobador ve solo lo suyo', () => {
    mockUser('comite_aprobador')
    renderEn('/payment-agreements')
    expect(menu()).toEqual(['Acuerdos', 'Gastos', 'Reservaciones', 'Seguridad', 'Dudas', 'Reglamento'])
  })

  it('el comité de solo lectura no ve Reservaciones', () => {
    mockUser('comite_lectura')
    renderEn('/payment-agreements')
    expect(menu()).toEqual(['Acuerdos', 'Gastos', 'Seguridad', 'Dudas', 'Reglamento'])
  })

  it('escribir a mano la dirección de una sección ajena lleva al inicio del rol, sin mostrar su contenido', () => {
    mockUser('tesorero')
    renderEn('/users')
    expect(screen.queryByText('Contenido de Usuarios')).not.toBeInTheDocument()
    expect(screen.getByText('Contenido de Cobranza')).toBeInTheDocument()
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
