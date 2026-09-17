class TenantClabe {
  final String id;
  final String nombre;
  final String clabeDestino;

  TenantClabe({required this.id, required this.nombre, required this.clabeDestino});

  factory TenantClabe.fromJson(Map<String, dynamic> json) {
    return TenantClabe(
      id: json['id'] as String,
      nombre: json['nombre'] as String,
      clabeDestino: json['clabe_destino'] as String,
    );
  }
}
