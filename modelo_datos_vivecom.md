# Modelo de datos — Vivecom

**Tarea relacionada:** F0-07 — Diseñar modelo de datos (ERD) completo
**Estrategia multi-tenant:** schema-por-tenant en PostgreSQL (cada condominio = un schema aislado; las tablas de este documento se replican dentro de cada schema, salvo que se indique lo contrario)

---

## Núcleo

### tenant *(fuera del schema del tenant — vive en el schema público/control)*
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| nombre | varchar | Nombre del condominio |
| clabe_destino | varchar(18) | CLABE vigente para recibir transferencias |
| precio_por_vivienda | decimal(10,2) | $25 MXN IVA incluido (ver alcance §1) |
| schema_name | varchar | Nombre del schema PostgreSQL asignado |
| created_at | timestamp | |

### property
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| identificador | varchar | Ej. "Casa 14", "Depto 302" |
| referencia_pago | varchar(7), unique | Referencia numérica de SPEI para identificar de qué vivienda es un depósito, ya que todas transfieren a la misma CLABE del condominio — el residente la captura al transferir |
| saldo_a_favor | decimal(10,2), default 0 | Excedente cuando un depósito conciliado supera lo debido; se descuenta automáticamente del siguiente `fee_charge` que se genere |

### resident
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| nombre | varchar | |
| telefono | varchar | Usado para WhatsApp/SMS |
| email | varchar (nullable) | |

### resident_property *(tabla puente N:N)*
| Campo | Tipo | Notas |
|---|---|---|
| resident_id | uuid FK → resident | |
| property_id | uuid FK → property | |
| rol | enum(propietario, inquilino) | |
| PK compuesta | (resident_id, property_id) | Un residente con varias viviendas tiene una fila por cada una — **cada vivienda se administra de forma independiente** (alcance §2) |

### user_account
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| resident_id | uuid FK → resident (nullable) | Null si es guardia/admin sin perfil de residente |
| email | varchar | Login |
| password_hash | varchar | |
| rol | enum(admin, tesorero, comite_lectura, comite_aprobador, vocero, residente, guardia) | Ver HU-A06, HU-A07, HU-C02, HU-C07 |
| property_id | uuid FK → property (nullable) | Solo aplica a rol residente |
| created_at | timestamp | |

---

## Financiero

> **Nota de implementación (corregido contra el código real, antes desalineado):** el diseño que terminó
> implementándose es más simple de lo que describía esta sección originalmente — no existen tablas separadas
> `payment_allocation` ni `credit_balance`. Un pago anticipado de 1-12 meses simplemente crea de una vez varios
> `fee_charge` ya marcados `pagado`, todos con el mismo `payment_id` (relación 1-a-muchos: un `payment` puede
> saldar varios `fee_charge`, ver `payment_reconciliation_service._aplicar_pago_anticipado`). El saldo a favor
> tampoco es una tabla con historial: es un solo campo `saldo_a_favor` en `property`, que se incrementa cuando
> un depósito conciliado supera lo debido y se descuenta automáticamente del siguiente `fee_charge` que se genere.

### fee *(configuración de cuota)*
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| monto | decimal(10,2) | |
| periodicidad | enum(mensual, bimestral, semanal, unica) | `semanal` se elige pero hoy genera con la misma cadencia que `mensual` (no implementado de verdad, ver fee.py); `unica` es para cuotas extraordinarias — no compite por ser "la cuota vigente", genera un solo cargo |
| activa_desde | date | Para `unica`, es el periodo al que aplica ese cargo único, no una fecha de inicio |

### fee_charge *(cargo generado por ciclo)*
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| property_id | uuid FK → property | |
| fee_id | uuid FK → fee | |
| periodo | date | Primer día del mes/ciclo que corresponde |
| monto_base | decimal(10,2) | |
| recargo_aplicado | decimal(10,2) | 10% si no se pagó antes del minuto 1 del día 6 (regla global, HU-A04) |
| estado | enum(pendiente, pagado, vencido) | |
| payment_id | uuid FK → payment (nullable) | Se llena al conciliar el depósito que lo saldó; varios `fee_charge` pueden compartir el mismo `payment_id` (pago anticipado) |
| recordatorio_enviado_en | date (nullable) | Último recordatorio mandado — una vez al día, no en cada corrida del job |
| confirmacion_enviada | boolean | Si ya se avisó que este cargo quedó pagado (una sola vez, sin importar qué lo pagó) |

### payment
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| property_id | uuid FK → property (nullable) | Null si la referencia no coincide con ninguna vivienda — el pago se guarda igual para que el tesorero lo resuelva a mano (HU-A06), en vez de perderse |
| monto | decimal(10,2) | |
| estado | enum(pendiente, confirmado, rechazado) | `pendiente` = detectado pero sin conciliar (ej. referencia no reconocida) |
| referencia_recibida | varchar(7) | La referencia de 7 dígitos que el residente captura al transferir (ver `property.referencia_pago`) |
| clave_rastreo | varchar, unique | Identificador único de la transacción SPEI — evita procesar el mismo webhook dos veces si el proveedor lo reintenta |
| proveedor | varchar | Proveedor de recepción SPEI, default `"stp"` |
| fecha_deteccion | timestamp | Cuándo el proveedor confirmó el depósito |
| registrado_por | uuid (nullable) | Quién lo capturó a mano (efectivo, o una transferencia que el proveedor no detectó) — null en pagos detectados automáticamente |

### clabe_change_log *(auditoría, HU-A07 — vive en schema público junto a tenant)*
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| tenant_id | uuid FK → tenant | |
| clabe_anterior | varchar(18) | |
| clabe_nueva | varchar(18) | |
| cambiado_por | uuid FK → user_account | |
| fecha | timestamp | |

### expense
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| categoria | varchar | |
| monto | decimal(10,2) | |
| comprobante_url | varchar | **Obligatorio**, no nullable (alcance §3.1, HU-A09) |
| fecha | date | |

### budget
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| categoria | varchar | |
| periodicidad | enum(mensual, anual) | Mensual por defecto; anual para actividades específicas (HU-A10) |
| periodo | date | |
| monto_planeado | decimal(10,2) | |

---

## Seguridad

### access_log
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| property_id | uuid FK → property (nullable) | Null si es proveedor sin vivienda asociada |
| tipo | enum(residente, visitante, proveedor) | |
| hora_entrada | timestamp | |
| hora_salida | timestamp (nullable) | |

### visitor_qr
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| property_id | uuid FK → property | |
| codigo | varchar | |
| usado | boolean | Expira automáticamente al usarse una vez (HU-S02) |
| fecha_generado | timestamp | |
| fecha_usado | timestamp (nullable) | |

### vehicle
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| access_log_id | uuid FK → access_log | |
| placa | varchar | |

### package
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| property_id | uuid FK → property | |
| fecha_llegada | timestamp | Dispara notificación (HU-S05) |
| fecha_recogido | timestamp (nullable) | Dispara segunda notificación al cerrarse |

### incident
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| reportado_por | uuid FK → user_account | |
| estado | enum(abierta, en_proceso, resuelta) | Visible para admin y comité (HU-S06) |
| descripcion | text | |
| created_at | timestamp | |

### incident_update
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| incident_id | uuid FK → incident | |
| user_id | uuid FK → user_account | |
| comentario | text | |
| created_at | timestamp | |

---

## Comunicación

### announcement
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| titulo | varchar | |
| contenido | text | |
| fecha_publicacion | timestamp | |

### read_receipt
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| announcement_id | uuid FK → announcement | |
| property_id | uuid FK → property | |
| leido_at | timestamp | |

### poll
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| creado_por | uuid FK → user_account | Solo rol `vocero` (HU-C02) |
| pregunta | varchar | |
| fecha_cierre | date | |
| resultados_en_vivo | boolean | Configurable por votación (HU-C02) |
| quorum_alcanzado | boolean | Requiere 51% de participación |
| reactivada | boolean | Se reactiva 1 semana si no alcanza quorum (HU-C04) |

### poll_option
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| poll_id | uuid FK → poll | |
| texto | varchar | |

### vote
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| poll_id | uuid FK → poll | |
| property_id | uuid FK → property | |
| option_id | uuid FK → poll_option | |
| UNIQUE | (poll_id, property_id) | Un voto por vivienda (HU-C03) |

### lost_found_item
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| publicado_por | uuid FK → user_account | |
| descripcion | text | |
| foto_url | varchar (nullable) | |
| estado | enum(pendiente_autorizacion, autorizado, rechazado) | Moderado por admin (HU-C05) |

### amenity
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| nombre | varchar | |
| periodo_limite_horas | int | Tiempo límite de respuesta para aprobación (HU-C07) |

### reservation
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| amenity_id | uuid FK → amenity | |
| property_id | uuid FK → property | |
| fecha_inicio | timestamp | |
| fecha_fin | timestamp | Duración configurable (uno o varios días) |
| estado | enum(pendiente, aprobada, rechazada, expirada) | Rechazo automático si nadie responde a tiempo (HU-C07) |
| aprobador_id | uuid FK → user_account (nullable) | Quién la aprobó/rechazó |

### amenity_approver *(tabla puente: qué miembros del comité aprueban qué amenidad)*
| Campo | Tipo | Notas |
|---|---|---|
| amenity_id | uuid FK → amenity | |
| user_id | uuid FK → user_account | Debe tener rol `comite_aprobador` |
| PK compuesta | (amenity_id, user_id) | |

---

## Notas de implementación

- **Multi-tenancy**: `tenant` y `clabe_change_log` viven en un schema público de control; todas las demás tablas se crean dentro del schema propio de cada condominio (`tenant.schema_name`).
- **Índices recomendados desde el día 1**: `fee_charge(property_id, periodo)`, `payment(clabe_virtual)`, `access_log(property_id, hora_entrada)`, `vote(poll_id, property_id)` (ya cubierto por el UNIQUE).
- **Campos de auditoría** (`created_at`, y `updated_at` donde aplique) se omitieron de varias tablas por brevedad, pero deben incluirse en todas.
