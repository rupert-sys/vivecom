class TenantConfig {
  final String id;
  final String nombre;
  final bool tieneLogo;

  TenantConfig({required this.id, required this.nombre, required this.tieneLogo});

  factory TenantConfig.fromJson(Map<String, dynamic> json) {
    return TenantConfig(
      id: json['id'] as String,
      nombre: json['nombre'] as String,
      tieneLogo: json['tiene_logo'] as bool,
    );
  }
}
