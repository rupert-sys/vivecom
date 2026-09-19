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
  // Dudas de los residentes: las activa la administración por aviso.
  final bool permiteDudas;
  final bool dudasAbiertas; // ¿se pueden mandar HOY? (activadas y dentro del plazo)

  Announcement({
    required this.id,
    required this.titulo,
    required this.contenido,
    required this.fechaPublicacion,
    required this.leido,
    this.permiteDudas = false,
    this.dudasAbiertas = false,
  });

  Announcement copyWith({bool? leido}) => Announcement(
    id: id,
    titulo: titulo,
    contenido: contenido,
    fechaPublicacion: fechaPublicacion,
    leido: leido ?? this.leido,
    permiteDudas: permiteDudas,
    dudasAbiertas: dudasAbiertas,
  );

  factory Announcement.fromJson(Map<String, dynamic> json) {
    return Announcement(
      id: json['id'] as String,
      titulo: json['titulo'] as String,
      contenido: json['contenido'] as String,
      fechaPublicacion: utcNaiveToDateTime(json['fecha_publicacion'] as String),
      leido: json['leido'] as bool?,
      permiteDudas: (json['permite_dudas'] as bool?) ?? false,
      dudasAbiertas: (json['dudas_abiertas'] as bool?) ?? false,
    );
  }
}
