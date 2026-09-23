import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { RequireAuth } from './RequireAuth'
import { useAuth } from './AuthContext'

vi.mock('./AuthContext', () => ({ useAuth: vi.fn() }))

function mockUser(user: Partial<ReturnType<typeof useAuth>['user']> | null) {
  vi.mocked(useAuth).mockReturnValue({
    user: user as ReturnType<typeof useAuth>['user'],
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function renderEn(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route path="/login" element={<p>Pantalla de login</p>} />
        <Route path="/cambiar-password" element={<RequireAuth><p>Cambiar contraseña</p></RequireAuth>} />
        <Route path="/properties" element={<RequireAuth><p>Contenido de Viviendas</p></RequireAuth>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireAuth', () => {
  it('sin sesión, manda a login', () => {
    mockUser(null)
    renderEn('/properties')
    expect(screen.getByText('Pantalla de login')).toBeInTheDocument()
  })

  it('con sesión normal, deja ver el contenido', () => {
    mockUser({ sub: 'u1', tenant_id: 't1', schema: 's1', rol: 'admin', property_id: null, debe_cambiar_password: false, exp: 0 })
    renderEn('/properties')
    expect(screen.getByText('Contenido de Viviendas')).toBeInTheDocument()
  })

  it('con debe_cambiar_password, manda a /cambiar-password aunque se pida otra ruta', () => {
    mockUser({ sub: 'u1', tenant_id: 't1', schema: 's1', rol: 'admin', property_id: null, debe_cambiar_password: true, exp: 0 })
    renderEn('/properties')
    expect(screen.getByText('Cambiar contraseña')).toBeInTheDocument()
  })

  it('con debe_cambiar_password, /cambiar-password sí se puede ver (si no, nunca se podría cambiar)', () => {
    mockUser({ sub: 'u1', tenant_id: 't1', schema: 's1', rol: 'admin', property_id: null, debe_cambiar_password: true, exp: 0 })
    renderEn('/cambiar-password')
    expect(screen.getByText('Cambiar contraseña')).toBeInTheDocument()
  })
})
