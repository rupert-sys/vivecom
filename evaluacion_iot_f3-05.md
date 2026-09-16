# Evaluación de integraciones IoT (F3-05)

**Tarea relacionada:** F3-05 — "Explorar cámaras y control de acceso biométrico como add-on" (rol Tech Lead, depende de F2-01).

Esta es una evaluación técnica, no una implementación: F3-05 pide explorar la viabilidad, no construir el add-on todavía.

## Contexto

F2-01 a F2-04 ya cubren el control de acceso base (guardia registra entradas/salidas a mano, QR de un solo uso para visitantes, vehículos asociados). Este documento evalúa si vale la pena automatizar esa captura con cámaras y/o biometría, y bajo qué condiciones.

## 1. Cámaras de videovigilancia

**Recomendación: viable a corto plazo, como integración — no como producto propio.**

- No construir DVR/firmware propio. Integrar vía la API de un proveedor VSaaS existente (ej. UniFi Protect, Verkada, Rhombus — UniFi tiene la documentación más abierta y es común en instalaciones residenciales/condominios en México).
- Cada condominio compra y es dueño de su propio hardware y suscripción; Vivecom solo consume su API para mostrar/enlazar clips relevantes (ej. asociar una grabación al momento de un `AccessLog` o de una `Incident`).
- Complejidad de integración: baja-media. El patrón ya existe en el proyecto — un webhook que recibe un evento del proveedor y lo asocia a un registro existente, igual que `payments_providers/stp.py` (F1-06) recibe depósitos.
- Consideración legal: videovigilancia de áreas comunes es una práctica ya establecida y menos sensible que biometría bajo LFPDPPP — no exige el mismo nivel de consentimiento explícito reforzado.

**Siguiente paso sugerido si se prioriza:** un prototipo con un solo proveedor (UniFi Protect), reusando el patrón de webhook + `AccessLog` de F2-01, antes de comprometerse con una integración multi-proveedor.

## 2. Control de acceso biométrico (huella/rostro)

**Recomendación: técnicamente viable, pero con una carga de cumplimiento real que no se debe subestimar.**

- Hardware: paneles de acceso con reconocimiento facial/huella (ZKTeco, Hikvision, Suprema) que exponen API/webhook — el mismo patrón de integración que las cámaras.
- **Diseño recomendado: emparejamiento en el borde (edge), nunca en Vivecom.** El dispositivo hace el match localmente y solo manda un evento tipo "residente X reconocido, hora Y" — Vivecom jamás almacena la plantilla biométrica ni la imagen fuente. Esto reduce significativamente (aunque no elimina) la exposición legal de Vivecom como responsable del dato.
- **Punto crítico de cumplimiento:** la LFPDPPP clasifica los datos biométricos como **datos personales sensibles**, que requieren consentimiento **expreso y por escrito** — un nivel más estricto que el aviso de privacidad general de F3-02. El flujo de consentimiento de F3-02 (aceptar un aviso genérico) **no alcanza** para biometría; haría falta un flujo de consentimiento separado y explícito, revisado por un abogado, antes de activar esta función con cualquier residente real.

**Recomendación de priorización:** no construir esto todavía. Esperar a que haya demanda real de un condominio pagando por el servicio, y conseguir revisión legal del flujo de consentimiento reforzado, antes de invertir en la integración de hardware.

## Resumen

| Opción | Viabilidad técnica | Complejidad | Riesgo legal (LFPDPPP) | Prioridad sugerida |
|---|---|---|---|---|
| Cámaras (vía API de proveedor) | Alta | Baja-media | Bajo (ya es práctica común) | Corto plazo, si hay demanda |
| Biometría (edge-matching) | Alta | Media | **Alto** (dato sensible, consentimiento reforzado) | Esperar demanda real + revisión legal |

Ninguna de las dos requiere construir hardware ni firmware propio — ambas son integraciones vía la API de un proveedor externo, reusando el patrón de webhook ya establecido en el proyecto desde F1-06.
