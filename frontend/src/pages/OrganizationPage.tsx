import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { deleteLogo, fetchLogoObjectUrl, getTenantConfig, updateTenantName, uploadLogo } from '../api/tenant'

const TIPOS_DE_LOGO_ACEPTADOS = 'image/jpeg,image/png,image/webp'
const MAX_LOGO_MB = 3

export function OrganizationPage() {
  const [nombre, setNombre] = useState('')
  const [nombreGuardado, setNombreGuardado] = useState('')
  const [tieneLogo, setTieneLogo] = useState(false)
  const [logoUrl, setLogoUrl] = useState<string | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [guardandoNombre, setGuardandoNombre] = useState(false)
  const [subiendoLogo, setSubiendoLogo] = useState(false)

  async function reload() {
    setLoading(true)
    try {
      const config = await getTenantConfig()
      setNombre(config.nombre)
      setNombreGuardado(config.nombre)
      setTieneLogo(config.tiene_logo)
      setLogoUrl(config.tiene_logo ? await fetchLogoObjectUrl() : null)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar la configuración del condominio.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
    // Los object URL del logo se liberan al desmontar o al reemplazarse (reload/handleLogoChange/handleQuitarLogo).
  }, [])

  async function handleGuardarNombre(event: FormEvent) {
    event.preventDefault()
    setGuardandoNombre(true)
    setAviso(null)
    try {
      const config = await updateTenantName(nombre)
      setNombreGuardado(config.nombre)
      setNombre(config.nombre)
      setAviso('Nombre actualizado.')
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el nombre.')
    } finally {
      setGuardandoNombre(false)
    }
  }

  async function handleLogoChange(archivo: File | null) {
    if (!archivo) return
    setSubiendoLogo(true)
    setAviso(null)
    try {
      const config = await uploadLogo(archivo)
      setTieneLogo(config.tiene_logo)
      setLogoUrl((anterior) => {
        if (anterior) URL.revokeObjectURL(anterior)
        return URL.createObjectURL(archivo)
      })
      setAviso('Logo actualizado.')
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo subir el logo.')
    } finally {
      setSubiendoLogo(false)
    }
  }

  async function handleQuitarLogo() {
    if (!window.confirm('¿Quitar el logo del condominio?')) return
    try {
      await deleteLogo()
      setLogoUrl((anterior) => {
        if (anterior) URL.revokeObjectURL(anterior)
        return null
      })
      setTieneLogo(false)
      setAviso('Logo eliminado.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo quitar el logo.')
    }
  }

  if (loading) return <p>Cargando…</p>

  return (
    <div>
      <h2>Organización</h2>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 560 }}>
        El nombre y el logo aparecen en el encabezado del panel para todos los que inician sesión en este condominio.
      </p>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}
      {aviso && <p style={{ color: 'var(--teal-strong)' }}>{aviso}</p>}

      <div className="card" style={{ padding: 'var(--space-4)', maxWidth: 480, marginTop: 'var(--space-3)' }}>
        <h3>Nombre del condominio</h3>
        <form onSubmit={handleGuardarNombre} style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input
            aria-label="Nombre del condominio"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={guardandoNombre || nombre.trim() === nombreGuardado}>
            {guardandoNombre ? 'Guardando…' : 'Guardar'}
          </button>
        </form>
      </div>

      <div className="card" style={{ padding: 'var(--space-4)', maxWidth: 480, marginTop: 'var(--space-3)' }}>
        <h3>Logo</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
          <div
            style={{
              width: 64, height: 64, borderRadius: 'var(--radius)', border: '1px solid var(--border-soft)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', flexShrink: 0,
              background: 'var(--surface-2)',
            }}
          >
            {logoUrl ? (
              <img src={logoUrl} alt="Logo del condominio" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <span style={{ color: 'var(--ink-faint)', fontSize: '0.75rem' }}>Sin logo</span>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <input
              aria-label="Logo del condominio"
              type="file"
              accept={TIPOS_DE_LOGO_ACEPTADOS}
              disabled={subiendoLogo}
              onChange={(e) => handleLogoChange(e.target.files?.[0] ?? null)}
            />
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--ink-faint)' }}>
              JPG, PNG o WEBP, hasta {MAX_LOGO_MB} MB.
            </p>
            {tieneLogo && (
              <button type="button" onClick={handleQuitarLogo} style={{ color: 'var(--brick)', alignSelf: 'flex-start' }}>
                Quitar logo
              </button>
            )}
          </div>
        </div>
        {subiendoLogo && <p style={{ margin: 0 }}>Subiendo…</p>}
      </div>
    </div>
  )
}
