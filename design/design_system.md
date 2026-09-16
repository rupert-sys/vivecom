# Sistema de diseño — Vivecom

**Tarea relacionada:** F0-10

## Concepto
Vivecom administra dinero, seguridad y comunicación oficial de un condominio — necesita transmitir **confianza y claridad**, no un feel de "app social". Inspiración: bitácora de operación / ledger, no dashboard corporativo genérico.

## Paleta
| Token | Hex | Uso |
|---|---|---|
| `--ink` | #1C2A39 | Texto principal, headers |
| `--ink-soft` | #5C6773 | Texto secundario |
| `--paper` | #F6F4EE | Fondo base |
| `--surface` | #FFFFFF | Tarjetas |
| `--border` | #D8D3C4 | Bordes, separadores |
| `--teal` (éxito/pagado) | #2F6F5E | Pagos confirmados, aprobaciones |
| `--amber` (pendiente) | #9A6B1F | Estados pendientes, en progreso |
| `--brick` (alerta/vencido) | #A6432F | Recargos, rechazos, incidencias urgentes |
| `--dustblue` (informativo) | #3E5C76 | Avisos, información neutra |

## Tipografía
- **Encabezados**: "Source Serif 4" — da formalidad tipo documento oficial de condominio.
- **Datos/cifras/IDs**: "IBM Plex Mono" — montos, folios, CLABE, fechas técnicas.
- **Cuerpo**: sans-serif del sistema (San Francisco / Roboto según plataforma).

## Componentes base
- **Tarjeta de estado** (pagado/pendiente/vencido/rechazado): franja de color a la izquierda + ícono + monto en mono.
- **Botón primario**: `--teal` para acciones de confirmación (pagar, aprobar); `--brick` reservado solo para acciones destructivas.
- **Badge de rol**: chip con iniciales (T=Tesorero, V=Vocero, A=Administrador, G=Guardia).
- **Timeline de incidencia**: puntos conectados por línea vertical, con el estado actual resaltado.

## Iconografía
Set de línea simple (ej. Tabler Icons) — evitar ilustraciones o iconos "playful", este es software operativo, no consumo.
