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
        <Route path="/" element={<RequireAuth><p>Listado de condominios</p></RequireAuth>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireAuth', () => {
  it('sin sesión, manda a login', () => {
    mockUser(null)
    renderEn('/')
    expect(screen.getByText('Pantalla de login')).toBeInTheDocument()
  })

  it('con sesión de staff, deja ver el contenido', () => {
    mockUser({ sub: 's1', staff: true, exp: 0 })
    renderEn('/')
    expect(screen.getByText('Listado de condominios')).toBeInTheDocument()
  })
})
