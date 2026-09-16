# Guía de contribución — Vivecom

**Tarea relacionada:** F0-13 — Configurar repositorios y estrategia de branching

## Estrategia de repositorio: monorepo

Un solo repositorio para todo (`backend/`, `design/`, `infra/`, `.github/`, documentos de
producto en la raíz). Se eligió monorepo en vez de multi-repo porque:
- El proyecto ya vive así físicamente desde Fase 0 (ver estructura en `README.md`).
- Backend, infraestructura y documentación de producto avanzan juntos y a menudo un
  mismo cambio los toca a los tres (ej. F1-06 cambió backend y dejó nota en
  `modelo_datos_vivecom.md`).
- Un solo equipo pequeño trabajando en todo el MVP no necesita el aislamiento de
  permisos/versionado que justifica separar repos — eso se reconsiderará si `frontend/`
  o `mobile/` se vuelven proyectos con su propio ciclo de release independiente.

## Branching: trunk-based

- **`main`** es la única rama de larga vida. Siempre debe quedar en estado desplegable
  (es lo que corre el pipeline de CI/CD de F0-14).
- Todo trabajo nuevo va en una rama corta creada desde `main`, nombrada:

  ```
  <tipo>/<id-de-tarea>-<slug-corto>
  ```

  Ejemplos reales de este proyecto:
  - `feat/F1-13-recordatorios-pago`
  - `fix/F2-20-race-reservaciones`
  - `docs/F3-05-evaluacion-iot`

  `<tipo>` es uno de: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
  `<id-de-tarea>` es el ID exacto del plan de trabajo (`bitacora_vivecom.html` /
  `plan_de_trabajo_vivecom.xlsx`), para poder rastrear cualquier línea de código hasta
  la tarea que la originó. Si el trabajo no corresponde a ninguna tarea del plan
  (un fix chico encontrado de pasada), se omite el ID: `fix/warning-pytest-asyncio`.
- Ramas de vida corta: se abren, se trabajan y se cierran (merge o descarte) en días,
  no semanas — evita divergencias grandes de `main`.
- Merge a `main` vía Pull Request, con **squash merge** (un commit limpio por rama en
  el historial de `main`, aunque la rama haya tenido commits intermedios desordenados).

## Convención de commits

Formato [Conventional Commits](https://www.conventionalcommits.org/), adaptado con el
ID de tarea entre paréntesis en vez del scope técnico:

```
<tipo>(<id-de-tarea>): <resumen en español, en infinitivo/imperativo>
```

Ejemplos:
```
feat(F1-07): conciliación automática de pagos contra FeeCharge
fix(F2-20): candado anti-carrera en resolve_reservation
docs(F0-13): estrategia de branching y convención de commits
test(F1-13): confirmaciones de pago no se marcan enviadas si falla el proveedor
```

Mismos `<tipo>` que en el nombre de rama. Si el commit cierra o avanza una tarea del
plan, el ID va entre paréntesis; si no aplica a ninguna, se omite el paréntesis.

## Protección de la rama `main`

Esto queda **documentado aquí como la política a aplicar**, pero no se puede configurar
todavía: la protección de ramas es una opción del repositorio real en GitHub/GitLab
(Settings → Branches), y este repo hoy solo existe en local — crear el remoto real
sigue pendiente de acción humana (ver `README.md`, sección "Pendiente de configurar").

Política a aplicar en cuanto exista el remoto:
- Prohibir push directo a `main`: todo cambio entra por Pull Request.
- Requerir que el pipeline de CI (`.github/workflows/ci.yml`, de F0-14) pase en verde
  antes de poder hacer merge.
- Requerir al menos 1 aprobación de otra persona antes de hacer merge (aplica en cuanto
  el equipo tenga más de una persona con acceso de escritura).
- Prohibir force-push e historial reescrito sobre `main`.
