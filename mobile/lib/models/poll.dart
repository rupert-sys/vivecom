class PollOption {
  final String id;
  final String texto;

  PollOption({required this.id, required this.texto});

  factory PollOption.fromJson(Map<String, dynamic> json) {
    return PollOption(id: json['id'] as String, texto: json['texto'] as String);
  }
}

class Poll {
  final String id;
  final String pregunta;
  final DateTime fechaCierre; // solo fecha, sin hora
  final bool resultadosEnVivo;
  final bool quorumAlcanzado;
  final bool reactivada;
  final List<PollOption> opciones;
  final bool? yaVoto;
  // Reglamento: la vivienda en mora conserva voz pero no voto. null si no aplica.
  final bool? votoRestringidoPorMora;

  Poll({
    required this.id,
    required this.pregunta,
    required this.fechaCierre,
    required this.resultadosEnVivo,
    required this.quorumAlcanzado,
    required this.reactivada,
    required this.opciones,
    required this.yaVoto,
    this.votoRestringidoPorMora,
  });

  factory Poll.fromJson(Map<String, dynamic> json) {
    return Poll(
      id: json['id'] as String,
      pregunta: json['pregunta'] as String,
      fechaCierre: DateTime.parse(json['fecha_cierre'] as String),
      resultadosEnVivo: json['resultados_en_vivo'] as bool,
      quorumAlcanzado: json['quorum_alcanzado'] as bool,
      reactivada: json['reactivada'] as bool,
      opciones: (json['opciones'] as List).map((e) => PollOption.fromJson(e as Map<String, dynamic>)).toList(),
      yaVoto: json['ya_voto'] as bool?,
      votoRestringidoPorMora: json['voto_restringido_por_mora'] as bool?,
    );
  }

  bool get cerrada => quorumAlcanzado || !fechaCierre.isAfter(DateTime.now());

  // Una votación abierta en la que esta vivienda todavía puede y no ha votado.
  bool get pendienteDeVotar => !cerrada && yaVoto != true && votoRestringidoPorMora != true;
}

class PollResultOption {
  final String optionId;
  final String texto;
  final int votos;

  PollResultOption({required this.optionId, required this.texto, required this.votos});

  factory PollResultOption.fromJson(Map<String, dynamic> json) {
    return PollResultOption(
      optionId: json['option_id'] as String,
      texto: json['texto'] as String,
      votos: json['votos'] as int,
    );
  }
}

class PollResults {
  final String pollId;
  final int totalVotos;
  final List<PollResultOption> resultados;

  PollResults({required this.pollId, required this.totalVotos, required this.resultados});

  factory PollResults.fromJson(Map<String, dynamic> json) {
    return PollResults(
      pollId: json['poll_id'] as String,
      totalVotos: json['total_votos'] as int,
      resultados: (json['resultados'] as List)
          .map((e) => PollResultOption.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
