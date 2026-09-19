import 'package:flutter/material.dart';

import '../models/poll.dart';
import '../services/api_client.dart';
import '../services/poll_service.dart';
import '../utils/dates.dart';

class PollsScreen extends StatefulWidget {
  final String token;
  final PollService pollService;
  // Avisa cuántas votaciones abiertas le faltan por votar a esta vivienda, para
  // que la barra de navegación lo señale (el residente no sabía dónde votar).
  final ValueChanged<int>? onPendientesCambiaron;

  const PollsScreen({super.key, required this.token, required this.pollService, this.onPendientesCambiaron});

  @override
  State<PollsScreen> createState() => _PollsScreenState();
}

class _PollsScreenState extends State<PollsScreen> {
  List<Poll>? _votaciones;
  String? _error;
  bool _cargando = true;

  final Map<String, String> _opcionSeleccionada = {};
  final Map<String, bool> _votando = {};
  final Map<String, String> _errorPorVotacion = {};
  final Map<String, PollResults> _resultados = {};
  final Map<String, String> _errorResultados = {};

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final votaciones = await widget.pollService.listarVotaciones(widget.token);
      if (!mounted) return;
      setState(() => _votaciones = votaciones);
      widget.onPendientesCambiaron?.call(votaciones.where((v) => v.pendienteDeVotar).length);
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudieron cargar las votaciones.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _votar(Poll poll) async {
    final opcion = _opcionSeleccionada[poll.id];
    if (opcion == null) return;
    setState(() {
      _votando[poll.id] = true;
      _errorPorVotacion.remove(poll.id);
    });
    try {
      await widget.pollService.votar(poll.id, opcion, widget.token);
      await _cargar();
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorPorVotacion[poll.id] = err is ApiException ? err.message : 'No se pudo registrar el voto.');
    } finally {
      if (mounted) setState(() => _votando[poll.id] = false);
    }
  }

  Future<void> _verResultados(Poll poll) async {
    try {
      final resultados = await widget.pollService.obtenerResultados(poll.id, widget.token);
      if (!mounted) return;
      setState(() => _resultados[poll.id] = resultados);
    } catch (err) {
      if (!mounted) return;
      setState(() {
        _errorResultados[poll.id] = err is ApiException
            ? err.message
            : 'No se pudieron cargar los resultados.';
      });
    }
  }

  // Sin Scaffold/AppBar propios: ver la nota en announcements_screen.dart.
  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(onRefresh: _cargar, child: _buildBody());
  }

  Widget _buildBody() {
    if (_cargando && _votaciones == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _votaciones == null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        ],
      );
    }
    final votaciones = _votaciones!;
    if (votaciones.isEmpty) {
      return ListView(
        children: const [Padding(padding: EdgeInsets.all(24), child: Text('Todavía no hay votaciones.'))],
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: votaciones.length,
      separatorBuilder: (_, _) => const Divider(),
      itemBuilder: (context, indice) => _buildVotacion(votaciones[indice]),
    );
  }

  Widget _buildVotacion(Poll poll) {
    return Card(
      key: Key('votacion_${poll.id}'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(poll.pregunta, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Cierra: ${formatoFechaCorta(poll.fechaCierre)} · ${poll.cerrada ? 'Cerrada' : 'Abierta'}'),
            const SizedBox(height: 12),
            if (poll.yaVoto == true || poll.cerrada)
              _buildResultadosOControl(poll)
            else if (poll.votoRestringidoPorMora == true)
              _buildVotoRestringido()
            else
              _buildFormularioVoto(poll),
          ],
        ),
      ),
    );
  }

  // Reglamento: la vivienda con cuotas vencidas conserva voz pero no voto.
  // Se explica aquí en vez de dejar que el residente toque "Votar" y reciba un error.
  Widget _buildVotoRestringido() {
    return Container(
      key: const Key('voto_restringido'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(8)),
      child: const Text(
        'Tu vivienda tiene cuotas vencidas, así que por reglamento conservas voz pero no voto. '
        'Ponte al corriente en Pago para poder votar.',
      ),
    );
  }

  Widget _buildFormularioVoto(Poll poll) {
    final votando = _votando[poll.id] == true;
    final error = _errorPorVotacion[poll.id];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ...poll.opciones.map(
          (opcion) => RadioListTile<String>(
            key: Key('opcion_${opcion.id}'),
            title: Text(opcion.texto),
            value: opcion.id,
            groupValue: _opcionSeleccionada[poll.id],
            onChanged: (valor) => setState(() => _opcionSeleccionada[poll.id] = valor!),
          ),
        ),
        if (error != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(error, style: const TextStyle(color: Colors.red))),
        ElevatedButton(
          onPressed: (votando || _opcionSeleccionada[poll.id] == null) ? null : () => _votar(poll),
          child: Text(votando ? 'Votando…' : 'Votar'),
        ),
      ],
    );
  }

  Widget _buildResultadosOControl(Poll poll) {
    final resultados = _resultados[poll.id];
    final errorResultados = _errorResultados[poll.id];
    if (resultados != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Total de votos: ${resultados.totalVotos}'),
          ...resultados.resultados.map((r) => Text('${r.texto}: ${r.votos}')),
        ],
      );
    }
    if (errorResultados != null) {
      return Text(errorResultados, style: const TextStyle(color: Colors.orange));
    }
    return Row(
      children: [
        if (poll.yaVoto == true) const Text('Ya votaste. '),
        TextButton(onPressed: () => _verResultados(poll), child: const Text('Ver resultados')),
      ],
    );
  }
}
