# Documento de alcance — Vivecom (México)

**Tarea relacionada:** F0-01 — Definir alcance detallado del MVP
**Estado:** ✅ Cerrado (v3.3) — 26 historias de usuario, incorpora hallazgos de entrevistas y, desde v3.3, el reglamento interior de cada condominio como configuración (sección 3.4), que **supera** cuatro decisiones anteriores (marcadas «superada por 3.4» abajo)
**Versión:** 3.3

---

## 1. Objetivo del proyecto

Vivecom es una plataforma que centraliza la administración, comunicación, seguridad y cobro de cuotas de un condominio o residencial en México, reemplazando hojas de cálculo, cuadernos de caseta y grupos de WhatsApp por un sistema único con visibilidad para el administrador y para cada residente.

**Problema que resuelve:**
- El administrador no tiene control financiero en tiempo real ni transparencia hacia los residentes.
- La caseta de seguridad lleva bitácoras en papel, sin trazabilidad ni reportes.
- La comunicación oficial se pierde entre grupos de WhatsApp sin confirmación de lectura ni historial.

**No resuelve (por ahora):** administración de mantenimiento correctivo/preventivo de instalaciones (elevadores, bombas, etc.) ni gestión de personal/nómina del condominio. Si esto es importante para ti, lo marcamos como candidato a una fase futura.

**Modelo de negocio:** el cobro de Vivecom es **por vivienda**, con periodicidad mensual (alineada al ciclo de la cuota de mantenimiento). No hay periodo de prueba gratuito. **Precio: $25 MXN por vivienda al mes, IVA incluido.** Cuota mínima mensual equivalente a **50 viviendas** ($1,250 MXN/mes IVA incluido) — los condominios con menos de 50 viviendas pagan esta cuota mínima.

---

## 2. Usuarios y roles

| Rol | Necesidad principal |
|---|---|
| Administrador del condominio | Ver y cobrar cuotas, comunicar avisos, revisar reportes de seguridad; confirma explícitamente cualquier cambio a la cuenta CLABE de destino |
| Tesorero (miembro del comité) | Valida los pagos detectados/registrados; resuelve casos especiales (rechazos, saldo a favor) |
| Comité / mesa directiva | Consultar reportes financieros en solo lectura (sin aprobar gastos, ver pregunta 2 resuelta); gestiona incidencias junto con el administrador; **uno o más miembros designados como aprobadores** aprueban o rechazan reservaciones de amenidades — este es el único flujo de aprobación del comité en el sistema |
| Vocero (representante de sección/edificio) | Crea las votaciones digitales |
| Residente (propietario o inquilino) | Ver su estado de cuenta, pagar, recibir avisos, reservar amenidades, votar, **consultar los gastos del condominio** |
| Guardia de caseta | Registrar accesos, visitantes, paquetería e incidencias |
| Proveedor / visitante | Acceso temporal vía QR, sin necesidad de cuenta |

**Resuelto:** un propietario puede tener 2 o más viviendas dentro del mismo condominio, pero cada vivienda se administra de forma **independiente** — cuotas, estado de cuenta, pagos y ocupante pueden ser distintos por vivienda, ya que el propietario puede rentar unas y habitar otra. Implicación de diseño: la relación entre `Resident` (persona) y `Property` (vivienda) es N:N, pero todo lo financiero, de accesos y de comunicación se ancla a la `Property`, nunca a la persona directamente. Si un propietario tiene 3 viviendas, ve 3 estados de cuenta separados, no uno consolidado (a menos que pidas una vista consolidada como mejora futura).

---

## 3. Alcance funcional — qué SÍ incluye el MVP y las fases siguientes

### 3.1 Administrativo

**Incluye:**
- Alta de condominio, viviendas y residentes (con relación propietario/inquilino).
- Configuración de cuotas: monto y periodicidad (mensual/bimestral) definidos por cada condominio; el recargo por atraso es, **por defecto**, 10% único a partir del minuto 1 del día 6 de cada mes (los primeros 5 días son de gracia) — *superada por 3.4:* cada condominio puede configurar día límite, porcentaje y modalidad (único o mensual sobre saldo) según su reglamento.
- Recordatorios automáticos de pago: se envían desde el día 1 del mes hasta que la vivienda registre su pago, por notificación dentro de la app del condominio (canal principal) y WhatsApp; SMS como respaldo si los anteriores fallan. En cuanto el pago se registra, se envía una confirmación de pago en vez de seguir mandando recordatorios de cobro.
- Pago anticipado: el residente puede pagar por adelantado de 1 a 12 meses en una sola transacción, precisamente para evitar que se generen recargos por mora en esos meses futuros.
- Generación automática de cargos por vivienda cada ciclo.
- Todos los pagos son por **transferencia bancaria (SPEI)** a la cuenta CLABE del condominio, que se muestra dentro de la app y es configurable por el administrador (modificable en cualquier momento, con **confirmación explícita del administrador** y registro en bitácora de auditoría). No hay pago en línea con tarjeta. *Pago en efectivo: superada por 3.4* — se acepta solo en los condominios cuyo reglamento lo prevé, y lo captura el tesorero (que entrega recibo).
- El residente hace la transferencia **desde su propio banco** (fuera de la app, como una transferencia normal) — no se requiere Open Banking ni que capture datos bancarios dentro de Vivecom. El pago se refleja automáticamente en su estado de cuenta en cuanto el sistema detecta el depósito (integración de recepción SPEI).
- El **tesorero** (rol del comité) es quien valida los pagos detectados y resuelve casos especiales. Si un residente transfiere de más, el excedente queda como **saldo a favor** para el siguiente periodo. Si la transferencia no se refleja de inmediato, queda en estado **"pendiente"** hasta que el sistema la detecte; si el banco la rechaza, el residente debe repetir la transferencia.
- Recibo de pago simple (no fiscal) generado automáticamente por cada pago registrado, descargable en PDF.
- Estado de cuenta por vivienda, consultable por el residente y el administrador.
- Registro de gastos del condominio por categoría, con comprobante **obligatorio** en todos los casos.
- **Transparencia de gastos para residentes**: cada residente puede consultar en qué se gastó el dinero del condominio (categoría, monto, comprobante), no solo el administrador — motivo principal de adopción según entrevistas (sección 13).
- Reporte de presupuesto vs. gasto real: el presupuesto se carga de forma **mensual** por defecto; para actividades específicas (ej. proyectos grandes) se puede definir a nivel **anual**.
- Exportación de reportes a Excel.

**No incluye (en ninguna fase planeada, salvo que lo pidas):**
- Facturación fiscal / timbrado CFDI de los pagos (confirmado contigo: no se requiere; sí se genera un recibo simple no fiscal, ver arriba).
- Nómina de personal del condominio (conserjes, jardineros, etc.).
- Contabilidad completa de doble entrada — solo exportación de pólizas para que el contador la use en su propio sistema (Fase 3).
- Vista consolidada de todas las viviendas de un mismo propietario (queda como mejora futura, fuera del MVP).

### 3.2 Seguridad

**Incluye:**
- Registro de entradas/salidas de residentes, visitantes y proveedores con hora exacta.
- Generación de QR de acceso temporal que el residente comparte con su visita; el QR **expira automáticamente al usarse** (un solo uso, no por fecha/hora). Sin límite de visitantes por vivienda ni restricción de horario de acceso — el sistema registra libremente, no bloquea por cantidad ni por hora.
- Registro de vehículos asociados a un acceso.
- Registro de paquetería recibida: se notifica al residente cuando llega, y se genera una notificación adicional cuando ya fue recogido, para cerrar el registro.
- Bitácora de incidencias con seguimiento (abierta → en proceso → resuelta). **Toda incidencia se gestiona junto con el comité**, no solo con el administrador.
- App de caseta funcional sin conexión a internet, que sincroniza al recuperarla. Si al sincronizar se detecta un error o conflicto (ej. registros duplicados), se notifica automáticamente al administrador.

**No incluye (por ahora):**
- Reconocimiento facial o biométrico (queda como evaluación futura, Fase 3).
- Integración con cámaras de videovigilancia existentes.
- Control de acceso físico automatizado (torniquetes, plumas) — el sistema registra, no abre puertas.

### 3.3 Comunicación

**Incluye:**
- Publicación de avisos y circulares, con confirmación de lectura por vivienda.
- Notificación dentro de la app del condominio (canal principal) y WhatsApp cuando se publica un aviso; SMS como respaldo si los anteriores fallan.
- Votaciones digitales, creadas por los **voceros** (representantes de sección/edificio), con fecha de cierre definida al crearlas. Requieren un **mínimo de 51% de participación** de las viviendas para ser válidas; si no se alcanza, la votación **se reactiva automáticamente una semana después** con un nuevo periodo de expiración, enviando recordatorios a todos los residentes para que participen. Si los resultados se muestran en tiempo real o solo al cierre depende de la configuración elegida en cada votación (no es un comportamiento fijo).
- Tablón de objetos perdidos y encontrados: las publicaciones requieren **autorización del administrador** antes de mostrarse públicamente.
- Calendario y reservación de amenidades (salón de eventos, alberca, cancha), con bloqueo para evitar doble reservación del mismo horario. Regla de anticipación por defecto: mínimo 2 días antes, salvo que el horario siga disponible más cerca de la fecha; *superada por 3.4:* cada amenidad puede exigir una anticipación mínima estricta (ej. 8 días), un horario máximo, días permitidos, capacidad y cuota. La reservación tiene una duración configurable (uno o varios días) y expira automáticamente al terminar ese periodo. **Toda reservación queda en estado "pendiente" hasta que se apruebe**: el administrador designa a uno o más miembros del comité como aprobadores (por amenidad o de forma general), y al solicitarse la reservación se les envía una notificación por los 3 canales definidos (app + WhatsApp + SMS de respaldo). Cada amenidad tiene su propio **periodo límite de respuesta configurable**; si nadie aprueba dentro de ese plazo, la reservación se **rechaza automáticamente**. El residente ve el estado de su reservación (pendiente/aprobada/rechazada) en todo momento, notificado por los mismos 3 canales.

**No incluye (por ahora):**
- Chat en tiempo real entre residentes (tipo mensajería instantánea). El WhatsApp mencionado arriba es solo para notificaciones automáticas de un solo sentido (avisos, recordatorios), no una conversación bidireccional dentro de la plataforma.
- Encuestas complejas con lógica condicional — solo votaciones de opción única.

---

### 3.4 Reglamento interior por condominio (v3.3)

Los administradores entregaron el reglamento interior real de un condominio (Arequipa, modificado el 18-ene-2026) y con él quedó claro que las reglas **cambian de condominio a condominio**. Por eso dejan de ser constantes de la plataforma y pasan a ser configuración por condominio (`PATCH /tenant/reglamento`, por amenidad en `PATCH /amenities/{id}`). Sin configurar, todo se comporta como antes (los valores por defecto reproducen las reglas globales de las versiones 3.2 y anteriores).

| Regla del reglamento | Cómo se refleja en Vivecom |
|---|---|
| Art. 9: cuota mensual con plazo hasta el día 5; recargo de 5% mensual sobre saldo | `dia_limite_pago`, `recargo_porcentaje`, `recargo_modalidad` (`unico` \| `mensual_sobre_saldo`). El recargo se recalcula en absoluto cada día (idempotente): monto base × % × meses vencidos. Hora local `America/Mexico_City`. |
| Art. 9 IV y Art. 7 VI: pago en efectivo con recibo | `acepta_pago_efectivo`; `POST /payments/manual` (tesorero) registra quién capturó el pago; el recibo PDF indica "Efectivo". |
| Art. 5 III: la vivienda en mora conserva voz pero no voto | `morosos_sin_voto`; votar responde 403 y `PollRead.voto_restringido_por_mora` deja que la app lo explique en vez de fallar. |
| Art. 2 III-VIII: área adoquinada — 8 días de anticipación, hasta la 01:00 am, cuota de $1,000, sin adeudos | Reglas por amenidad: `dias_anticipacion_minimos`, `hora_inicio_permitida`/`hora_fin_maxima` (cruza medianoche), `dias_semana_permitidos`, `capacidad`, `max_duracion_horas`, `cuota` (+ `cuota_pagada` que marca tesorería), `notas_reglamento`. `AmenityRead.reglas` las expone en lenguaje llano y `GET /amenities/{id}/disponibilidad` dice cuántos lugares quedan (ej. cajones). `morosos_sin_areas_comunes` bloquea a la vivienda con adeudo. |
| Art. 2 IX-XI y Art. 17 V.7: 7 cajones de visitas, máximo 24 h | `cajones_visitas`, `horas_max_estacionamiento_visitas`; `GET /access-log/estacionamiento-visitas` (libres y accesos que ya rebasaron el plazo). |
| Art. 17 V.1-V.3: bitácora con nombre, acompañantes, identificación y autorización previa | `AccessLog.nombre_visitante`, `acompanantes`, `identificacion`, `autorizado_por` (`residente_previo` \| `telefono` \| `otro`). |
| Art. 17 V.2: bitácora de incidencias con casa y persona; la caseta reporta fallas | `Incident.tipo` (`seguridad` \| `mantenimiento` \| `otro`), `property_id`, `persona_involucrada`; filtros por tipo y vivienda. Reportar una falla no es administrar el mantenimiento (sigue fuera de alcance). |
| Art. 8: gastos programados/extraordinarios > $10,000 requieren asamblea y 3 cotizaciones; remisión o factura | `gasto_umbral_asamblea`, `cotizaciones_minimas`; `Expense.tipo`, `aprobado_en_asamblea`, `acta_referencia`, `cotizaciones`, `tipo_comprobante`. |
| Art. 7 VI: estado de cuenta cuatrimestral a cada condómino | `GET /expenses/summary?desde&hasta` (ingresos, gastos, saldo a favor o en contra, por cobrar, gastos por tipo y categoría), abierto a todo rol autenticado. |
| Cobranza: quién pagó, quién falta, quién es moroso | `GET /reports/collection-status` (tesorero/admin): por vivienda `al_corriente` \| `pendiente` \| `moroso`, adeudo y conteos. Moroso se calcula por fecha, no depende de que el job diario ya haya corrido. |
| Art. 16: constancia de no adeudo para la venta | `GET /reports/no-debt-certificate/{property_id}` — PDF NO fiscal; 409 si hay cualquier cargo sin pagar. |

**Interpretaciones a confirmar con el cliente:** (1) "5% mensual sobre saldo" se modeló como interés simple sobre el monto base por cada mes vencido, no compuesto; (2) el reglamento fija 8 días de anticipación **mínimos** (antes era solo informativo); (3) la prórroga de cuotas (Art. 1 VIII y 9 VII) **no está implementada**: falta definir quién la solicita, quién la aprueba y cómo afecta el recargo y el estatus de moroso; (4) la restricción a morosos es solo de **voto y áreas comunes** — Vivecom sigue sin negar el acceso físico a la vivienda ni a sus visitas (ver la nota «No construir» de la sección 13); (5) la caseta offline no puede conocer la mora, por lo que no bloquea accesos.

**App residente (implementado):** reglas y disponibilidad en reservaciones, cuota de cada reservación y si tesorería la recibió, aviso de mora con sus restricciones en el estado de cuenta, explicación de por qué no se puede votar y una insignia con las votaciones por votar, resumen financiero en gastos, y una pestaña «Visitas y paquetes» donde el residente genera el QR de un solo uso para su visita y ve sus paquetes en la caseta.

**App caseta (implementado):** bitácora con nombre, acompañantes, identificación y autorización; cajones de visitas libres; incidencias de seguridad o mantenimiento con casa y persona; paquetería (llegada offline, aviso al residente, entrega); y códigos QR de un solo uso que el guardia emite a proveedores, con la validación mostrando a quién se deja pasar y a dónde. La caseta no bloquea accesos por adeudo (sección 13, «No construir»).

**Panel admin (implementado):** página Reglamento (configuración de las reglas del condominio), Cobranza (quién pagó, quién falta, quién es moroso, con constancia de no adeudo), Gastos con resumen financiero y sustento (asamblea y cotizaciones), Amenidades con sus reglas, Reservaciones con las cuotas de uso que tesorería recibe, Seguridad con tipo de incidencia, datos de la bitácora y cajones de visitas, y en el detalle de cada vivienda su estado de cuenta con el aviso de mora y el registro de pagos en efectivo.

**Comprobantes como archivo (implementado):** el administrador adjunta la foto o el PDF de cada gasto (y de sus cotizaciones), y el residente adjunta la captura o el PDF de su transferencia desde la app: tesorería lo revisa y lo acepta (se registra el pago) o lo rechaza con un motivo. Un comprobante nunca concilia por sí solo, y aceptarlo avisa si el SPEI ya detectó ese mismo pago para no contarlo dos veces. La caseta también adjunta una foto a cada incidencia (con la cámara, y sin conexión: la foto se guarda en el teléfono y se sube al sincronizar). Se aceptan fotos (JPG, PNG, WEBP, HEIC) y PDF de hasta 10 MB; los archivos viven en un almacenamiento privado (disco local en desarrollo, S3 en producción) y se abren con enlaces firmados de vida corta.

**Pendiente de producto (retroalimentación de administradores, sin implementar):** retroalimentación/preguntas en avisos (el alcance excluye chat: falta decidir un formato acotado); resumen de paquetes en el panel admin.

---

## 4. Requisitos no funcionales

- **Disponibilidad:** el sistema debe operar de forma confiable incluso si la caseta pierde conexión (offline-first en esa app).
- **Seguridad de datos:** cumplimiento de la Ley Federal de Protección de Datos Personales (LFPDPPP) — aviso de privacidad, consentimiento, derecho de acceso/borrado.
- **Seguridad de pagos:** ya no aplica cumplimiento PCI-DSS (no se procesan pagos con tarjeta). Como la cuenta de destino (CLABE) es un dato sensible y modificable, cualquier cambio debe quedar registrado en una bitácora de auditoría (quién lo cambió y cuándo).
- **Escalabilidad:** la arquitectura debe soportar múltiples condominios (multi-tenant) desde el día uno, aunque el lanzamiento sea con pocos clientes.
- **Idioma:** español (México) en toda la interfaz.
- **Dispositivos soportados:** app móvil iOS y Android para residentes y guardias; panel web para administradores (navegadores modernos, sin soporte a Internet Explorer).

---

## 5. Supuestos

- El condominio ya tiene definida su cuota de mantenimiento y reglamento interno; el sistema no define esas reglas, solo las administra.
- El administrador es responsable de dar de alta correctamente las viviendas y residentes iniciales (no hay migración automática desde otro sistema en el MVP).
- El administrador es responsable de mantener actualizada la cuenta bancaria (CLABE) a la que los residentes deben transferir, y de conciliar los pagos recibidos.

---

## 6. Restricciones

- Presupuesto y equipo: desarrollo apoyado por Claude/Claude Code, sin equipo dedicado de QA manual — las pruebas dependen de los pilotos reales.
- Fecha de referencia de arranque: definida en el plan de trabajo (hoja "Resumen" del Excel).
- Mercado: exclusivamente México en esta etapa; cualquier expansión a otro país es explícitamente fuera de alcance hasta nueva decisión.

---

## 7. Criterios de éxito del MVP

- Al menos 2-3 condominios piloto usando el módulo de cuotas y pagos durante un ciclo completo de cobro.
- Reducción medible del tiempo que el administrador dedica a conciliar pagos manualmente.
- Al menos el 70% de los residentes activos de un condominio piloto revisando su estado de cuenta desde la app.
- Cero incidentes de pago duplicado o no conciliado durante el piloto.

---

## 8. Preguntas abiertas para esta revisión

1. ~~¿Un residente puede tener más de una vivienda?~~ **Resuelto:** sí, y se tratan de forma independiente (ver sección 2).
2. ~~¿El comité/mesa directiva necesita aprobar gastos dentro del sistema, o solo consultarlos?~~ **Resuelto:** solo consultarlos. El comité tiene acceso de solo lectura a reportes financieros; no hay flujo de aprobación dentro del sistema.
3. ~~¿Los recargos por mora son iguales para todos los condominios o cada uno define su propia regla?~~ **Resuelto:** iguales para todos (regla global). *Superada por 3.4:* el reglamento del condominio Arequipa fija 5% mensual sobre saldo insoluto, así que la regla es configurable por condominio; el 10% único queda como valor por defecto.
4. ~~¿Existe algún reglamento de condominio (ej. límite de visitantes, horario de amenidades) que deba reflejarse como regla del sistema desde el MVP?~~ **Resuelto:** no hay límite de visitantes ni horario restringido de acceso. Las amenidades se reservan con mínimo 2 días de antelación, salvo que el horario siga disponible más cerca de la fecha (en cuyo caso sí se permite reservar con menos anticipación). La reservación expira automáticamente al terminar el bloque de tiempo programado, que puede ser de uno o varios días.
5. ~~¿Confirmas que no se requiere ningún tipo de comprobante fiscal, ni siquiera un recibo simple no fiscal generado por Vivecom?~~ **Resuelto:** sí se requiere un recibo simple (no fiscal) por cada pago; no se requiere timbrado ni CFDI.

---

## 9. Pendientes por documentar (lista de seguimiento)

Vamos marcando esta lista conforme resolvamos cada punto — es el "qué falta" vivo del documento.

- [x] **Reglamento del condominio (detalle):** sin límite de visitantes, sin horario restringido de acceso. Amenidades: mínimo 2 días de antelación para reservar (o menos si el horario sigue disponible), con expiración automática al terminar el bloque de tiempo reservado (uno o varios días). Ver sección 3.2 y 3.3.
- [x] **Historias de usuario y criterios de aceptación — Administrativo:** ver sección 10.1 (11 historias, HU-A01 a HU-A11).
- [x] **Historias de usuario y criterios de aceptación — Seguridad:** ver sección 10.2 (7 historias, HU-S01 a HU-S07).
- [x] **Historias de usuario y criterios de aceptación — Comunicación:** ver sección 10.3 (7 historias, HU-C01 a HU-C07).
- [x] **Monto/porcentaje del recargo por mora:** 10% de recargo global, aplicado a partir del minuto 1 del día 6 de cada mes (5 días de gracia). Recordatorios automáticos desde el día 1 hasta que se pague, y confirmación al registrarse el pago. Ver sección 3.1.
- [x] **Recargo en cuotas bimestrales:** el recargo se evalúa mes a mes según la regla del día 6, sin importar la periodicidad de facturación. Como el residente puede pagar por adelantado de 1 a 12 meses (ver sección 3.1), esta es la forma prevista de evitar el recargo en meses futuros, incluso en condominios con cuota bimestral.
- [x] **Vista consolidada para propietarios con varias viviendas:** queda fuera del MVP, como mejora futura.
- [x] **Modelo de negocio y pricing:** cobro por vivienda, con periodicidad mensual. Ver sección 1.
- [x] **Canal de notificación prioritario:** notificación dentro de la app del condominio (canal principal) y WhatsApp; SMS como respaldo si los anteriores fallan.
- [x] **Periodo de prueba / onboarding comercial:** no hay periodo gratuito.
- [x] **Pago en efectivo:** no existe por defecto (transferencia SPEI). *Superada por 3.4:* se habilita por condominio cuando su reglamento lo acepta. Ver sección 3.1.
- [x] **Seguridad al cambiar la cuenta de destino:** requiere confirmación explícita del administrador, además de quedar en la bitácora de auditoría.
- [x] **Proveedor de pagos:** no se requiere Open Banking ni iniciación de transferencias desde la app. El residente transfiere desde su propio banco (fuera de Vivecom) a la CLABE mostrada; solo se necesita un proveedor de **recepción/detección SPEI** (mucho más simple que iniciar transferencias) — el proveedor específico (STP, Arcus, etc.) se evalúa como parte de F0-05.
- [x] **Flujo de aprobación de reservaciones — destinatario:** el administrador designa a uno o más miembros del comité como aprobadores (no todo el comité por defecto).
- [x] **Flujo de aprobación de reservaciones — tiempo límite:** cada amenidad tiene su propio periodo límite de respuesta (configurable); si nadie aprueba a tiempo, se rechaza automáticamente.

---

## 10. Historias de usuario y criterios de aceptación

### 10.1 Administrativo

**HU-A01 — Ver estado de cuenta**
Como residente, quiero ver mi estado de cuenta, para saber cuánto debo y desde cuándo.
- Muestra cargos generados, pagos recibidos, recargos aplicados y saldo actual (o saldo a favor, si existe).
- Si el residente tiene varias viviendas, cada una se muestra por separado.

**HU-A02 — Recordatorios de pago**
Como residente, quiero recibir recordatorios desde el día 1 del mes, para no incurrir en recargos.
- Se envían por app (principal) y WhatsApp; SMS si los anteriores fallan.
- Se detienen en cuanto se registra el pago, y en su lugar se envía una confirmación.

**HU-A03 — Ver cuenta de destino**
Como residente, quiero ver la CLABE vigente del condominio dentro de la app, para transferir mi cuota.
- Se muestra el banco y CLABE actuales.
- Si el administrador la cambia, se refleja de inmediato para todos los residentes.

**HU-A04 — Pago reflejado automáticamente**
Como residente, quiero que mi transferencia se refleje sola en mi estado de cuenta, para no tener que subir comprobantes.
- Al detectarse el depósito (integración de recepción SPEI), el pago se marca como confirmado automáticamente.
- Si no se detecta de inmediato, el pago queda en estado "pendiente".
- Si el banco rechaza la transferencia, se notifica al residente para que la repita.

**HU-A05 — Pago anticipado**
Como residente, quiero pagar por adelantado de 1 a 12 meses en una sola operación, para evitar recargos futuros.
- El residente elige cuántos meses cubrir (1-12).
- El sistema aplica el pago a los cargos futuros correspondientes, sin que se genere el recargo del día 6 en esos meses.

**HU-A06 — Validación de pagos por el tesorero**
Como tesorero, quiero ver los pagos detectados, para confirmarlos o resolver casos especiales.
- Lista de pagos recientes con su estado (confirmado, pendiente, rechazado).
- Puede marcar un caso como saldo a favor cuando el monto transferido excede lo debido.

**HU-A07 — Cambio seguro de cuenta CLABE**
Como administrador, quiero cambiar la cuenta de destino con una confirmación explícita, para evitar cambios accidentales o fraudulentos.
- El cambio requiere una confirmación explícita (no se guarda con solo editar el campo).
- Queda registrado en una bitácora de auditoría: quién lo cambió, cuándo, y los valores anterior/nuevo.

**HU-A08 — Recibo simple**
Como residente, quiero recibir un recibo (no fiscal) por cada pago, para tener respaldo documental.
- Se genera automáticamente en PDF al confirmarse el pago.
- Descargable por el residente y visible para el administrador/tesorero.

**HU-A09 — Registro de gastos con comprobante**
Como administrador, quiero registrar los gastos del condominio con comprobante obligatorio, para mantener transparencia ante los residentes.
- No se puede guardar un gasto sin adjuntar comprobante.
- Cada gasto se clasifica por categoría.

**HU-A10 — Presupuesto vs. real**
Como administrador, quiero comparar el presupuesto contra el gasto real, para controlar las finanzas.
- El presupuesto se carga mensualmente por defecto.
- Ciertas actividades pueden definirse con presupuesto anual en vez de mensual.
- El reporte compara planeado vs. real por categoría y periodo.

**HU-A11 — Exportar reportes**
Como administrador, quiero exportar el estado de cuenta y los gastos a Excel, para compartirlos con el comité o el contador.
- Exportación filtrable por rango de fechas y por vivienda/categoría.

**HU-A12 — Transparencia de gastos**
Como residente, quiero ver los gastos del condominio, para confiar en que mi cuota se usa bien.
- Lista de gastos con categoría, monto y comprobante, visible para cualquier residente (no solo el administrador).
- No es editable por el residente — es una vista de solo lectura.
- Se puede filtrar por periodo (mes/año).

### 10.2 Seguridad

**HU-S01 — Registro de accesos**
Como guardia, quiero registrar entradas y salidas con hora exacta, para tener trazabilidad de la operación.
- Sin límite de visitantes por vivienda ni restricción de horario de acceso.

**HU-S02 — QR de acceso temporal**
Como residente, quiero generar un QR para mi visita, para que pueda entrar sin que yo la reciba en la caseta.
- El QR expira automáticamente al usarse una sola vez.
- Un QR ya usado no puede volver a escanearse.

**HU-S03 — Validación de QR en caseta**
Como guardia, quiero escanear el QR del visitante, para autorizar su acceso.
- Si el QR ya fue usado, expiró o no existe, el sistema lo rechaza y lo indica claramente.

**HU-S04 — Registro de vehículos**
Como guardia, quiero asociar un vehículo a un acceso, para tener el dato disponible en caso de incidente.

**HU-S05 — Paquetería**
Como residente, quiero que me notifiquen cuando llega un paquete, para ir a recogerlo.
- Notificación al momento de recibirse el paquete.
- Notificación adicional cuando se marca como recogido, cerrando el registro.

**HU-S06 — Incidencias compartidas con el comité**
Como guardia, quiero registrar una incidencia con seguimiento, para que quede documentada y se resuelva.
- Toda incidencia es visible tanto para el administrador como para el comité (no solo las urgentes).
- Estados: abierta → en proceso → resuelta.

**HU-S07 — App de caseta offline**
Como guardia, quiero que la app funcione sin conexión, para no detener mi trabajo si falla el internet.
- Los registros se guardan localmente y se sincronizan al recuperar conexión.
- Si al sincronizar se detecta un conflicto o error (ej. registros duplicados), se notifica automáticamente al administrador.

### 10.3 Comunicación

**HU-C01 — Avisos con confirmación de lectura**
Como residente, quiero recibir avisos oficiales y que quede registro de que los leí, para estar informado y que el administrador sepa que me llegó.
- Notificación por app (principal) y WhatsApp; SMS como respaldo.
- El administrador puede ver qué viviendas ya leyeron cada aviso.

**HU-C02 — Crear votación**
Como vocero, quiero crear una votación con fecha de cierre, para que la comunidad decida sobre un tema.
- Se define pregunta, opciones, fecha de cierre, y si los resultados se muestran en tiempo real o solo al cierre (configurable por votación).

**HU-C03 — Votar**
Como residente, quiero votar una sola vez por vivienda, para que el resultado sea representativo.

**HU-C04 — Quorum y reactivación automática**
Como vocero, quiero que la votación se reactive si no alcanza el quorum, para no perder el esfuerzo de organizarla.
- Si al cierre no se alcanzó un mínimo de 51% de participación, la votación se reabre automáticamente una semana después con un nuevo periodo de expiración.
- Se envían recordatorios a todos los residentes invitándolos a participar.

**HU-C05 — Objetos perdidos moderados**
Como residente, quiero publicar un objeto perdido o encontrado, para que otros lo vean.
- La publicación no aparece públicamente hasta que el administrador la autoriza.

**HU-C06 — Reservar amenidad**
Como residente, quiero reservar una amenidad con al menos 2 días de anticipación (o menos si sigue disponible), para asegurar el espacio.
- No se permite doble reservación del mismo horario.
- La duración es configurable (uno o varios días) y expira automáticamente al terminar.

**HU-C07 — Aprobación de reservación**
Como aprobador (miembro del comité designado), quiero recibir una notificación cuando alguien solicita una amenidad, para aprobarla o rechazarla a tiempo.
- Notificación por los 3 canales definidos (app, WhatsApp, SMS de respaldo).
- Si nadie responde dentro del periodo límite configurado para esa amenidad, la reservación se rechaza automáticamente.
- El residente ve el estado de su reservación (pendiente/aprobada/rechazada) en todo momento.

---

## 11. Panorama competitivo (investigación de mercado)

*Tarea relacionada: F0-02 — Investigación de competidores.*

### Competidores directos en México

| Plataforma | Origen | Precio aprox. | Fortaleza | Debilidad |
|---|---|---|---|---|
| **Koti** | Mexicana | $19 MXN + IVA/unidad/mes, precio único | Control de acceso QR "avanzado" y app dedicada para guardias | Precio por unidad sube el costo en condominios grandes |
| **ComunidadFeliz** | Chilena, fuerte en México | Por cotización | +7,000 condominios en México; acepta tarjeta, SPEI y OXXO con conciliación automática | QR calificado como "básico" frente a Koti |
| **Neivor** | Colombiana, expandida a México | Por cotización | Mejor PropTech del Año (GRI Club); escala de 25 a 2,200+ unidades | Sin app dedicada para guardias ni control QR fuerte |
| **AdminCondo** | Mexicana | Desde $999 MXN/mes (50 unidades) hasta $1,899 (200 unidades) | Interfón IP/WebRTC guardia-residente-administración, único en el mercado | Nicho de precio medio-alto |
| **Residentia** | Mexicana | ~$18-22 MXN/unidad/mes | Control de acceso QR, gestión de incidencias | Funciones más limitadas en general |
| **Vivook** (competidor real, no confundir con nuestro proyecto) | LATAM, 13 países | Desde $545 MXN/mes hasta 15 viviendas | +10 años en el mercado, ~2,000 condominios activos, se posiciona como #1 de LATAM | Gestión financiera "básica" en comparativas; integración SPEI menos directa |
| **Birrex** | Mexicana | Por cotización | Control de accesos muy completo (tags, QR, foto), pensado para el guardia | Menos enfocado en lo financiero |
| **Casandra** | Mexicana | Por cotización | Conexión con todos los bancos de México, emisión de CFDI | Sí requiere facturación fiscal (nosotros decidimos que no aplica) |

*Nota: parte de esta comparación proviene del blog de Koti, que se posiciona favorablemente a sí mismo — se toma como referencia, no como verdad absoluta.*

### Implicaciones para Vivecom

**Ajuste de estrategia:** la conciliación automática vía SPEI, que se asumía como diferenciador, **no lo es** — ComunidadFeliz y AdminCondo ya la ofrecen. Es tabla de apuestas mínima para competir, no ventaja.

**Diferenciación real disponible con lo ya definido en este documento:**
- Roles específicos de **tesorero** y **vocero** (mesa directiva mexicana) — ningún competidor investigado los modela; todos usan roles genéricos de "admin" y "comité".
- **Quorum del 51% con reactivación automática** de votaciones — lógica de negocio no observada en la competencia.
- **Sin facturación fiscal** — simplifica y abarata el desarrollo frente a competidores como Casandra o ComunidadFeliz.
- **WhatsApp + SMS sin correo electrónico** — más alineado al hábito real de comunicación en México.

**Desventaja de entrada a considerar:** Koti ya tiene app de guardia + QR avanzado (lo que nosotros planeamos para Fase 2), y AdminCondo tiene interfón IP que ningún otro competidor ofrece, incluido nuestro alcance actual.

---

## 12. Decisiones técnicas confirmadas

*Tareas relacionadas: F0-05 (stack tecnológico) y F0-06 (estrategia multi-tenant).*

| Capa | Decisión |
|---|---|
| Backend | Python (FastAPI) |
| Base de datos | PostgreSQL, **schema-por-tenant** (aislamiento por condominio) |
| App móvil (residente + guardia) | Flutter — elegido por su soporte maduro de almacenamiento local/offline, clave para la app de caseta sin conexión |
| Panel admin | React + TypeScript |
| Cola/jobs asíncronos | Redis + Celery |
| Notificaciones | WhatsApp Business API (Twilio/360dialog) + SMS de respaldo |
| Pagos (recepción SPEI) | **STP** como primera opción a evaluar (CLABE única por cliente, cobranza identificada); **Fintoc** como plan B si la integración se complica; Arcus descartado por ahora por no ofrecer alta de cuenta de prueba autoservicio |
| Infraestructura | AWS |

---

## 13. Hallazgos de entrevistas con administradores (cerrado)

*Tarea relacionada: F0-03 — cerrada con 2 entrevistas. Detalle completo en `resultados_entrevistas.md`.*

**Se cerraron las entrevistas en 2**, por decisión de negocio: las respuestas fueron consistentes entre sí y el mercado objetivo parece homogéneo en este perfil de administrador. Si el negocio se expande a un segmento distinto (administradoras profesionales grandes, fraccionamientos de lujo), vale la pena retomar entrevistas ahí.

**Validado con confianza razonable:**
- **Transparencia de gastos es el motor real de adopción** — ya incorporado como HU-A12 (sección 10.1).
- El tesorero ya cobra y da recibo manualmente en ambos casos — valida HU-A06 y HU-A08.
- Precio validado positivamente ("$25 es razonable"), con disposición real a pilotar primero.
- Hoy no existe registro digital de accesos/incidencias en ningún caso — valida la oportunidad, aunque implica cambio de hábito.

**Riesgos abiertos — resueltos:**
1. ~~¿Se reabre "todo pago es por transferencia"?~~ **Decisión: se mantiene** como valor por defecto (solo transferencia). *Superada por 3.4:* un condominio cuyo reglamento acepta efectivo lo activa en su configuración.
2. ~~¿Votaciones digitales vs. junta física con acta firmada?~~ **Decisión: se mantiene digital.** El módulo de votaciones (HU-C02 a HU-C04) queda como está; no se adapta al proceso de acta en papel.

**No construir**: un administrador reveló que hoy se niega el acceso físico a quien no paga — práctica con riesgo legal que Vivecom **no debe replicar** aunque algún cliente lo pida.

---

*Este documento se irá actualizando conforme lo revisemos. Cualquier cambio aquí puede implicar ajustes en el plan de trabajo y en la bitácora de tareas.*
