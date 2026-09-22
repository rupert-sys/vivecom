import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createProperty, deleteProperty, listProperties } from '../api/properties'
import { downloadImportTemplate, importResidents, type ResidentImportResult } from '../api/residentImport'
import { ApiError } from '../api/client'
import { StatCard } from '../components/StatCard'
import { useAuth } from '../auth/AuthContext'
import type { Property } from '../types'

function resumenDeOcupacion(properties: Property[]) {
  const propietario = properties.filter((p) => p.residente_principal_rol === 'propietario').length
  const inquilino = properties.filter((p) => p.residente_principal_rol === 'inquilino').length
  return { total: properties.length, propietario, inquilino, sinResidente: properties.length - propietario - inquilino }
}

export function PropertiesPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nuevoIdentificador, setNuevoIdentificador] = useState('')
  const [creating, setCreating] = useState(false)

  const [archivoImportar, setArchivoImportar] = useState<File | null>(null)
  const [importando, setImportando] = useState(false)
  const [resultadoImportacion, setResultadoImportacion] = useState<ResidentImportResult | null>(null)
  const [errorImportacion, setErrorImportacion] = useState<string | null>(null)

  async function reload() {
    setLoading(true)
    try {
      setProperties(await listProperties())
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar las viviendas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setCreating(true)
    try {
      await createProperty(nuevoIdentificador)
      setNuevoIdentificador('')
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la vivienda.')
    } finally {
      setCreating(false)
    }
  }

  async function handleDescargarPlantilla() {
    try {
      await downloadImportTemplate()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo descargar la plantilla.')
    }
  }

  async function handleImportar(event: FormEvent) {
    event.preventDefault()
    if (!archivoImportar) return
    setImportando(true)
    setErrorImportacion(null)
    setResultadoImportacion(null)
    try {
      const resultado = await importResidents(archivoImportar)
      setResultadoImportacion(resultado)
      setArchivoImportar(null)
      await reload()
    } catch (err) {
      setErrorImportacion(err instanceof ApiError ? err.message : 'No se pudo importar el archivo.')
    } finally {
      setImportando(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('¿Eliminar esta vivienda? Esta acción no se puede deshacer.')) return
    try {
      await deleteProperty(id)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar la vivienda.')
    }
  }

  return (
    <div>
      <h2>Viviendas</h2>
      {error && <p style={{ color: 'var(--brick)' }}>{error}</p>}

      {isAdmin && (
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: 'var(--space-2)', margin: 'var(--space-3) 0' }}>
          <input
            placeholder="Identificador (ej. Casa 12)"
            value={nuevoIdentificador}
            onChange={(e) => setNuevoIdentificador(e.target.value)}
            required
          />
          <button type="submit" disabled={creating}>
            {creating ? 'Creando…' : 'Agregar vivienda'}
          </button>
        </form>
      )}

      {isAdmin && (
        <details style={{ margin: 'var(--space-3) 0' }}>
          <summary>Importar Excel de condóminos</summary>
          <div style={{ marginTop: 'var(--space-2)', display: 'grid', gap: 'var(--space-2)', maxWidth: 480 }}>
            <p style={{ margin: 0 }}>
              Sube un Excel con nombre, teléfono, correo, si es propietario o inquilino, y el número de casa de cada
              condómino. Crea las viviendas y los residentes que falten, y liga a cada quien con su vivienda; una
              vivienda o un residente que ya existan no se duplican.{' '}
              <button type="button" onClick={handleDescargarPlantilla} style={{ padding: 0, textDecoration: 'underline' }}>
                Descargar plantilla
              </button>
            </p>
            <form onSubmit={handleImportar} aria-label="Importar Excel" style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
              <input
                type="file"
                aria-label="Archivo de Excel"
                accept=".xlsx,.xlsm"
                onChange={(e) => setArchivoImportar(e.target.files?.[0] ?? null)}
              />
              <button type="submit" disabled={!archivoImportar || importando}>
                {importando ? 'Importando…' : 'Importar'}
              </button>
            </form>
            {errorImportacion && <p style={{ color: 'var(--brick)' }}>{errorImportacion}</p>}
            {resultadoImportacion && (
              <div key="resultado-importacion">
                <p style={{ margin: 0 }}>
                  {resultadoImportacion.total_filas} fila{resultadoImportacion.total_filas === 1 ? '' : 's'} de condóminos:{' '}
                  {resultadoImportacion.viviendas_creadas} vivienda{resultadoImportacion.viviendas_creadas === 1 ? '' : 's'} nueva
                  {resultadoImportacion.viviendas_creadas === 1 ? '' : 's'}, {resultadoImportacion.residentes_creados} residente
                  {resultadoImportacion.residentes_creados === 1 ? '' : 's'} nuevo{resultadoImportacion.residentes_creados === 1 ? '' : 's'}
                  {resultadoImportacion.residentes_actualizados > 0 && ` (${resultadoImportacion.residentes_actualizados} actualizados)`},{' '}
                  {resultadoImportacion.vinculos_creados + resultadoImportacion.vinculos_actualizados} vínculo
                  {resultadoImportacion.vinculos_creados + resultadoImportacion.vinculos_actualizados === 1 ? '' : 's'} con su vivienda.
                </p>
                {resultadoImportacion.filas_con_error.length > 0 && (
                  <>
                    <p style={{ margin: 'var(--space-2) 0 4px', color: 'var(--brick)' }}>
                      {resultadoImportacion.filas_con_error.length} fila
                      {resultadoImportacion.filas_con_error.length === 1 ? '' : 's'} no se pudo importar; corrígela
                      {resultadoImportacion.filas_con_error.length === 1 ? '' : 'n'} en el Excel y vuelve a subirlo:
                    </p>
                    <ul style={{ margin: 0, paddingLeft: '1.2em' }}>
                      {resultadoImportacion.filas_con_error.map((e) => (
                        <li key={e.fila}>
                          Fila {e.fila}: {e.motivo}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </details>
      )}

      {loading ? (
        <p>Cargando…</p>
      ) : properties.length === 0 ? (
        <p>Todavía no hay viviendas registradas.</p>
      ) : (
        <>
          {(() => {
            const resumen = resumenDeOcupacion(properties)
            return (
              <div
                role="group"
                aria-label="Resumen de ocupación"
                style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}
              >
                <StatCard label="Viviendas">{resumen.total}</StatCard>
                <StatCard label="De propietario" color="var(--teal-strong)">
                  {resumen.propietario}
                </StatCard>
                <StatCard label="Rentadas" color="var(--dustblue)">
                  {resumen.inquilino}
                </StatCard>
                {resumen.sinResidente > 0 && (
                  <StatCard label="Sin residente" color="var(--ink-faint)">
                    {resumen.sinResidente}
                  </StatCard>
                )}
              </div>
            )
          })()}
          <table style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>Identificador</th>
              <th>Residente</th>
              <th>Referencia de pago</th>
              <th>Saldo a favor</th>
              {isAdmin && <th />}
            </tr>
          </thead>
          <tbody>
            {properties.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/properties/${p.id}`}>{p.identificador}</Link>
                </td>
                <td>
                  {p.residente_principal ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      {p.residente_principal}
                      <span className={`chip ${p.residente_principal_rol === 'propietario' ? 'chip-teal' : 'chip-blue'}`}>
                        {p.residente_principal_rol === 'propietario' ? 'Propietario' : 'Inquilino'}
                      </span>
                      {p.total_residentes > 1 && (
                        <span className="chip chip-neutral">+{p.total_residentes - 1}</span>
                      )}
                    </span>
                  ) : (
                    <span style={{ color: 'var(--ink-faint)' }}>Sin residente</span>
                  )}
                </td>
                <td className="mono">{p.referencia_pago}</td>
                <td className="mono">${p.saldo_a_favor.toFixed(2)}</td>
                {isAdmin && (
                  <td>
                    <button onClick={() => handleDelete(p.id)} style={{ color: 'var(--brick)' }}>
                      Eliminar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        </>
      )}
    </div>
  )
}
