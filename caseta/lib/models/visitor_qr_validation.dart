import 'dart:convert';

class VisitorQrValidation {
  final bool valido;
  final String? motivo; // no_existe | ya_usado
  final String? propertyId;
  // Para que el guardia sepa a quién deja pasar y a dónde.
  final String? tipo; // visitante | proveedor
  final String? descripcion; // ej. "Plomería López" (códigos de proveedor)
  final String? vivienda; // ej. "Casa 4"
  final String? nombreVisitante;
  final int? numeroPersonas;
  final String? horarioEsperado;
  final String? nombreResidente;
  final String? telefonoResidente;

  VisitorQrValidation({
    required this.valido,
    required this.motivo,
    required this.propertyId,
    this.tipo,
    this.descripcion,
    this.vivienda,
    this.nombreVisitante,
    this.numeroPersonas,
    this.horarioEsperado,
    this.nombreResidente,
    this.telefonoResidente,
  });

  factory VisitorQrValidation.fromJson(Map<String, dynamic> json) {
    return VisitorQrValidation(
      valido: json['valido'] as bool,
      motivo: json['motivo'] as String?,
      propertyId: json['property_id'] as String?,
      tipo: json['tipo'] as String?,
      descripcion: json['descripcion'] as String?,
      vivienda: json['vivienda'] as String?,
      nombreVisitante: json['nombre_visitante'] as String?,
      numeroPersonas: json['numero_personas'] as int?,
      horarioEsperado: json['horario_esperado'] as String?,
      nombreResidente: json['nombre_residente'] as String?,
      telefonoResidente: json['telefono_residente'] as String?,
    );
  }
}

// Lo que trae el propio código QR de una visita (ver app_residente/lib/models/visit.dart,
// VisitorQr.qrPayload): permite al guardia leer quién es el visitante, a qué vivienda va y a quién
// llamar para confirmar, SIN conexión. Validar si el código ya se usó sigue necesitando estar en línea
// (solo el servidor lo sabe) — esto es solo lo que ya viene escrito en el propio código.
class VisitorQrOfflineInfo {
  final String codigo;
  final String? nombreVisitante;
  final int? numeroPersonas;
  final String? horarioEsperado;
  final String? vivienda;
  final String? nombreResidente;
  final String? telefonoResidente;

  VisitorQrOfflineInfo({
    required this.codigo,
    this.nombreVisitante,
    this.numeroPersonas,
    this.horarioEsperado,
    this.vivienda,
    this.nombreResidente,
    this.telefonoResidente,
  });

  // null si el texto escaneado no es un payload conocido (un código de proveedor, o un QR de visita
  // generado antes de que existiera este payload) — en ese caso se sigue validando tal cual, como antes.
  static VisitorQrOfflineInfo? intentarLeer(String textoEscaneado) {
    try {
      final data = jsonDecode(textoEscaneado);
      if (data is! Map<String, dynamic> || data['codigo'] is! String) return null;
      return VisitorQrOfflineInfo(
        codigo: data['codigo'] as String,
        nombreVisitante: data['nombre_visitante'] as String?,
        numeroPersonas: data['numero_personas'] as int?,
        horarioEsperado: data['horario_esperado'] as String?,
        vivienda: data['vivienda'] as String?,
        nombreResidente: data['nombre_residente'] as String?,
        telefonoResidente: data['telefono_residente'] as String?,
      );
    } catch (_) {
      return null;
    }
  }
}

// Código de un solo uso que el guardia emite a un proveedor.
class ProviderCode {
  final String codigo;
  final String descripcion;
  final String? propertyId;

  ProviderCode({required this.codigo, required this.descripcion, required this.propertyId});

  factory ProviderCode.fromJson(Map<String, dynamic> json) {
    return ProviderCode(
      codigo: json['codigo'] as String,
      descripcion: (json['descripcion'] as String?) ?? '',
      propertyId: json['property_id'] as String?,
    );
  }
}
