import '../utils/dates.dart';

class Announcement {
  final String id;
  final String titulo;
  final String contenido;
  final DateTime fechaPublicacion;
  // null para quien no es residente ligado a una vivienda (ver
  // backend/app/schemas/announcement.py) — no debería pasar en la app
  // residente, pero se modela como nullable para reflejar el contrato real.
  final bool? leido;

  Announcement({
    required this.id,
    required this.titulo,
    required this.contenido,
    required this.fechaPublicacion,
    required this.leido,
  });

  factory Announcement.fromJson(Map<String, dynamic> json) {
    return Announcement(
      id: json['id'] as String,
      titulo: json['titulo'] as String,
      contenido: json['contenido'] as String,
      fechaPublicacion: utcNaiveToDateTime(json['fecha_publicacion'] as String),
      leido: json['leido'] as bool?,
    );
  }
}
