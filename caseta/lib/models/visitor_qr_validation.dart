class VisitorQrValidation {
  final bool valido;
  final String? motivo; // no_existe | ya_usado
  final String? propertyId;

  VisitorQrValidation({required this.valido, required this.motivo, required this.propertyId});

  factory VisitorQrValidation.fromJson(Map<String, dynamic> json) {
    return VisitorQrValidation(
      valido: json['valido'] as bool,
      motivo: json['motivo'] as String?,
      propertyId: json['property_id'] as String?,
    );
  }
}
