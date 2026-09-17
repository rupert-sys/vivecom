class Property {
  final String id;
  final String identificador;

  Property({required this.id, required this.identificador});

  factory Property.fromJson(Map<String, dynamic> json) {
    return Property(id: json['id'] as String, identificador: json['identificador'] as String);
  }
}
