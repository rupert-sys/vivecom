class LostFoundItem {
  final String id;
  final String publicadoPor;
  final String descripcion;
  final String? fotoUrl;
  final String estado; // pendiente_autorizacion | autorizado | rechazado

  LostFoundItem({
    required this.id,
    required this.publicadoPor,
    required this.descripcion,
    required this.fotoUrl,
    required this.estado,
  });

  factory LostFoundItem.fromJson(Map<String, dynamic> json) {
    return LostFoundItem(
      id: json['id'] as String,
      publicadoPor: json['publicado_por'] as String,
      descripcion: json['descripcion'] as String,
      fotoUrl: json['foto_url'] as String?,
      estado: json['estado'] as String,
    );
  }
}
