class VisitorQrValidation {
  final bool valido;
  final String? motivo; // no_existe | ya_usado
  final String? propertyId;
  // Para que el guardia sepa a quién deja pasar y a dónde.
  final String? tipo; // visitante | proveedor
  final String? descripcion; // ej. "Plomería López" (códigos de proveedor)
  final String? vivienda; // ej. "Casa 4"

  VisitorQrValidation({
    required this.valido,
    required this.motivo,
    required this.propertyId,
    this.tipo,
    this.descripcion,
    this.vivienda,
  });

  factory VisitorQrValidation.fromJson(Map<String, dynamic> json) {
    return VisitorQrValidation(
      valido: json['valido'] as bool,
      motivo: json['motivo'] as String?,
      propertyId: json['property_id'] as String?,
      tipo: json['tipo'] as String?,
      descripcion: json['descripcion'] as String?,
      vivienda: json['vivienda'] as String?,
    );
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
