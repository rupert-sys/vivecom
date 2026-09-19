import '../utils/dates.dart';

// Duda de un residente sobre un aviso. Va solo a la administración y al comité; si la administración la
// publica como aclaración, los demás vecinos la ven sin nombre ni vivienda.
class AnnouncementQuestion {
  final String id;
  final String announcementId;
  final String? avisoTitulo;
  final String texto;
  final String estado; // abierta | respondida
  final String? respuesta;
  final DateTime? respondidoEn;
  final bool publica;
  final DateTime createdAt;
  final bool propia; // ¿es de MI vivienda?
  final bool respuestaNueva; // me respondieron y todavía no la he visto

  AnnouncementQuestion({
    required this.id,
    required this.announcementId,
    required this.avisoTitulo,
    required this.texto,
    required this.estado,
    required this.respuesta,
    required this.respondidoEn,
    required this.publica,
    required this.createdAt,
    required this.propia,
    required this.respuestaNueva,
  });

  bool get respondida => estado == 'respondida';

  AnnouncementQuestion copyWith({bool? respuestaNueva}) => AnnouncementQuestion(
    id: id,
    announcementId: announcementId,
    avisoTitulo: avisoTitulo,
    texto: texto,
    estado: estado,
    respuesta: respuesta,
    respondidoEn: respondidoEn,
    publica: publica,
    createdAt: createdAt,
    propia: propia,
    respuestaNueva: respuestaNueva ?? this.respuestaNueva,
  );

  factory AnnouncementQuestion.fromJson(Map<String, dynamic> json) {
    final respondido = json['respondido_en'] as String?;
    return AnnouncementQuestion(
      id: json['id'] as String,
      announcementId: json['announcement_id'] as String,
      avisoTitulo: json['aviso_titulo'] as String?,
      texto: json['texto'] as String,
      estado: json['estado'] as String,
      respuesta: json['respuesta'] as String?,
      respondidoEn: respondido == null ? null : utcNaiveToDateTime(respondido),
      publica: json['publica'] as bool,
      createdAt: utcNaiveToDateTime(json['created_at'] as String),
      propia: (json['propia'] as bool?) ?? false,
      respuestaNueva: (json['respuesta_nueva'] as bool?) ?? false,
    );
  }
}
