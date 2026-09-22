# Sistema de diseño — Vivecom

**Tarea relacionada:** F0-10 (evolucionado: panel con barra lateral + identidad del condominio, y la misma paleta
aplicada al tema nativo de la app — `mobile/lib/theme.dart` — y al acceso directo de iPhone/APK de Android)

## Concepto
Vivecom administra dinero, seguridad y comunicación oficial de un condominio — necesita transmitir **confianza y claridad**, no un feel de "app social". Inspiración: bitácora de operación / ledger, no dashboard corporativo genérico.

## Paleta
La misma paleta vive en tres lugares que deben mantenerse en sincronía: `frontend/src/styles/tokens.css` (panel),
`mobile/lib/theme.dart` (app, nativo y web) y `mobile/web/manifest.json` + `index.html` (acceso directo de iPhone).

| Token | Hex | Uso |
|---|---|---|
| `--ink` | #1C2A39 | Texto principal, headers |
| `--ink-2` | #16283A | Barra lateral del panel, AppBar de la app, acceso directo de iPhone (theme-color) |
| `--ink-soft` | #5C6773 | Texto secundario |
| `--ink-faint` | #8B93A0 | Texto terciario, placeholders |
| `--paper` | #F6F4EE | Fondo base, splash del acceso directo (background_color) |
| `--surface` / `--surface-2` | #FFFFFF / #FBFAF6 | Tarjetas / fila alterna y hover sutil |
| `--border` / `--border-soft` | #D8D3C4 / #E8E4D8 | Bordes, separadores |
| `--teal` / `--teal-strong` (éxito/pagado, acción primaria) | #2F6F5E / #24594B | Pagos confirmados, aprobaciones, botones de confirmar |
| `--amber` (pendiente) | #9A6B1F | Estados pendientes, en progreso |
| `--brick` / `--brick-strong` (alerta/vencido) | #A6432F / #8A3526 | Recargos, rechazos, incidencias urgentes, acciones destructivas |
| `--dustblue` (informativo) | #3E5C76 | Avisos, información neutra |

Cada color semántico trae una variante `-tint` (fondo tenue) para chips y alertas sin saturar la pantalla
(`--teal-tint`, `--amber-tint`, `--brick-tint`, `--dustblue-tint`).

## Tipografía
- **Encabezados**: "Source Serif 4" — da formalidad tipo documento oficial de condominio.
- **Datos/cifras/IDs**: "IBM Plex Mono" — montos, folios, CLABE, fechas técnicas.
- **Cuerpo**: sans-serif del sistema (San Francisco / Roboto según plataforma).

## Componentes base
- **Tarjeta de estado** (pagado/pendiente/vencido/rechazado): franja de color a la izquierda + ícono + monto en mono.
- **Botón primario**: `--teal` para acciones de confirmación (pagar, aprobar); `--brick` reservado solo para acciones destructivas. En el panel, `button[type="submit"]` recibe el tratamiento primario automáticamente (cubre Entrar/Guardar/Crear/Importar sin tocar cada página); un botón cuyo texto ya usa `--brick` (la convención de "Eliminar" en todo el panel) se queda en su variante clara con borde, para no leerse como un error del propio botón.
- **Chip** (`.chip` + `.chip-teal`/`.chip-amber`/`.chip-brick`/`.chip-blue`/`.chip-neutral`): fondo tenue + texto en la variante fuerte del color semántico — rol de ocupación (propietario/inquilino), estados, conteos.
- **Badge de rol**: chip con iniciales (T=Tesorero, V=Vocero, A=Administrador, G=Guardia).
- **Timeline de incidencia**: puntos conectados por línea vertical, con el estado actual resaltado.

## Identidad del condominio (nombre y logo)
Cada condominio (tenant) puede poner su propio nombre y logo (`PATCH /tenant`, `POST/GET/DELETE /tenant/logo`;
panel: página **Organización**, solo administrador). Se muestran en:
- El panel: parte superior de la barra lateral (`components/Layout.tsx`), con la inicial del nombre como
  marcador de posición si no hay logo.
- La app: nombre del condominio arriba del identificador de la vivienda en Estado de cuenta (`statement_screen.dart`) — es solo contexto, así que si la consulta falla la pantalla se ve completa igual, sin avisar del error.

El logo se sirve por su propia ruta autenticada (`GET /tenant/logo`, sin enlace firmado de vida corta como el
resto de los archivos: el encabezado lo necesita disponible toda la sesión) y se trae como blob → object URL,
tanto en el panel como en la app.

## Barra lateral del panel
Reemplaza la barra horizontal original: con más de 15 secciones posibles (una lista por rol, ver
`frontend/src/permisos.ts`), un menú horizontal se desbordaba. La barra (`--ink-2`, texto claro) trae arriba el
logo/nombre del condominio, en medio la navegación (resaltada la sección activa), y abajo el rol de la sesión y
"Cerrar sesión". El contenido principal queda en `--paper`, con las tarjetas en `--surface`.

## Iconografía
Set de línea simple (ej. Tabler Icons) — evitar ilustraciones o iconos "playful", este es software operativo, no consumo.
