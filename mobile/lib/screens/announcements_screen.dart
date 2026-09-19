import 'package:flutter/material.dart';

import '../models/announcement.dart';
import '../models/announcement_question.dart';
import '../services/announcement_service.dart';
import '../services/api_client.dart';
import '../utils/dates.dart';

class AnnouncementsScreen extends StatefulWidget {
  final String token;
  final AnnouncementService announcementService;
  // Avisa cuántas respuestas a mis dudas todavía no he visto, para señalarlo en la barra de navegación.
  final ValueChanged<int>? onRespuestasNuevas;

  const AnnouncementsScreen({
    super.key,
    required this.token,
    required this.announcementService,
    this.onRespuestasNuevas,
  });

  @override
  State<AnnouncementsScreen> createState() => _AnnouncementsScreenState();
}

class _AnnouncementsScreenState extends State<AnnouncementsScreen> {
  List<Announcement>? _avisos;
  String? _error;
  bool _cargando = true;

  // Dudas por aviso: se cargan al abrir cada uno.
  final Map<String, List<AnnouncementQuestion>> _dudas = {};
  final Set<String> _cargandoDudas = {};
  final Map<String, String> _errorDudas = {};

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
      final avisos = await widget.announcementService.listarAvisos(widget.token);
      if (!mounted) return;
      setState(() => _avisos = avisos);
      _recontarRespuestasNuevas();
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudieron cargar los avisos.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  // Es solo un indicador: si falla, la insignia simplemente no se actualiza.
  Future<void> _recontarRespuestasNuevas() async {
    try {
      final mias = await widget.announcementService.listarMisDudas(widget.token);
      if (mounted) widget.onRespuestasNuevas?.call(mias.where((d) => d.respuestaNueva).length);
    } catch (_) {}
  }

  Future<void> _cargarDudas(Announcement aviso) async {
    setState(() {
      _cargandoDudas.add(aviso.id);
      _errorDudas.remove(aviso.id);
    });
    try {
      final dudas = await widget.announcementService.listarDudas(aviso.id, widget.token);
      if (!mounted) return;
      setState(() => _dudas[aviso.id] = dudas);
      // Al verlas, las respuestas dejan de ser "nuevas" para el resto de la app (el chip de esta vista se queda).
      if (dudas.any((d) => d.propia && d.respuestaNueva)) {
        try {
          await widget.announcementService.marcarRespuestasVistas(aviso.id, widget.token);
          _recontarRespuestasNuevas();
        } catch (_) {}
      }
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorDudas[aviso.id] = err is ApiException ? err.message : 'No se pudieron cargar las dudas.');
    } finally {
      if (mounted) setState(() => _cargandoDudas.remove(aviso.id));
    }
  }

  Future<void> _preguntar(Announcement aviso) async {
    final enviada = await showDialog<bool>(
      context: context,
      builder: (_) =>
          _DudaDialog(enviar: (texto) => widget.announcementService.preguntar(aviso.id, texto, widget.token)),
    );
    if (enviada == true) await _cargarDudas(aviso);
  }

  Future<void> _marcarLeido(Announcement aviso) async {
    if (aviso.leido == true) return;
    try {
      await widget.announcementService.marcarLeido(aviso.id, widget.token);
      if (!mounted) return;
      setState(() {
        final indice = _avisos!.indexWhere((a) => a.id == aviso.id);
        if (indice != -1) _avisos![indice] = aviso.copyWith(leido: true);
      });
    } catch (_) {
      // Marcar como leído es un efecto secundario silencioso (igual que
      // abrir un correo) — si falla, el usuario ya vio el contenido de
      // todos modos; no vale la pena interrumpirlo con un error.
    }
  }

  // Sin Scaffold/AppBar propios: esta pantalla siempre vive dentro de
  // CommunityScreen (F2-19), que aporta un único AppBar+TabBar compartido
  // para sus 4 pestañas en vez de que cada una traiga el suyo.
  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(onRefresh: _cargar, child: _buildBody());
  }

  Widget _buildBody() {
    if (_cargando && _avisos == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _avisos == null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        ],
      );
    }
    final avisos = _avisos!;
    if (avisos.isEmpty) {
      return ListView(
        children: const [Padding(padding: EdgeInsets.all(24), child: Text('Todavía no hay avisos.'))],
      );
    }
    return ListView.separated(
      itemCount: avisos.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, indice) => _buildAviso(avisos[indice]),
    );
  }

  Widget _buildAviso(Announcement aviso) {
    final noLeido = aviso.leido == false;
    return ExpansionTile(
      key: Key('aviso_${aviso.id}'),
      onExpansionChanged: (abierto) {
        if (!abierto) return;
        _marcarLeido(aviso);
        if (aviso.permiteDudas && !_dudas.containsKey(aviso.id)) _cargarDudas(aviso);
      },
      leading: noLeido
          ? const Icon(Icons.circle, size: 10, color: Colors.blue, key: Key('punto_no_leido'))
          : const SizedBox(width: 10),
      title: Text(aviso.titulo, style: TextStyle(fontWeight: noLeido ? FontWeight.bold : FontWeight.normal)),
      subtitle: Text(formatoFechaCorta(aviso.fechaPublicacion)),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Align(alignment: Alignment.centerLeft, child: Text(aviso.contenido)),
        ),
        if (aviso.permiteDudas) _buildDudas(aviso),
      ],
    );
  }

  // Aclaraciones públicas + mis dudas + el botón para preguntar. Un canal acotado con la administración,
  // no un chat: solo ella ve las dudas, y una duda recibe una respuesta.
  Widget _buildDudas(Announcement aviso) {
    final dudas = _dudas[aviso.id] ?? [];
    final aclaraciones = dudas.where((d) => !d.propia).toList();
    final mias = dudas.where((d) => d.propia).toList();
    return Padding(
      key: Key('dudas_${aviso.id}'),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(),
          if (_cargandoDudas.contains(aviso.id)) const LinearProgressIndicator(),
          if (_errorDudas[aviso.id] != null) Text(_errorDudas[aviso.id]!, style: const TextStyle(color: Colors.red)),
          if (aclaraciones.isNotEmpty) ...[
            const Text('Aclaraciones', style: TextStyle(fontWeight: FontWeight.bold)),
            ...aclaraciones.map(
              (d) => ListTile(
                key: Key('aclaracion_${d.id}'),
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(d.texto),
                subtitle: Text('Administración: ${d.respuesta ?? ''}'),
              ),
            ),
          ],
          if (mias.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text('Tus dudas', style: TextStyle(fontWeight: FontWeight.bold)),
            ...mias.map(
              (d) => ListTile(
                key: Key('mi_duda_${d.id}'),
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(d.texto),
                subtitle: Text(d.respondida ? 'Administración: ${d.respuesta ?? ''}' : 'Sin responder todavía'),
                trailing: d.respuestaNueva
                    ? const Chip(
                        label: Text('Nueva'),
                        key: Key('respuesta_nueva'),
                        visualDensity: VisualDensity.compact,
                      )
                    : null,
              ),
            ),
          ],
          const SizedBox(height: 8),
          if (aviso.dudasAbiertas)
            OutlinedButton.icon(
              key: Key('duda_boton_${aviso.id}'),
              onPressed: () => _preguntar(aviso),
              icon: const Icon(Icons.help_outline),
              label: const Text('Tengo una duda'),
            )
          else
            const Text('Ya no se reciben dudas sobre este aviso.', key: Key('dudas_cerradas')),
        ],
      ),
    );
  }
}

// El diálogo es un widget aparte a propósito: es DUEÑO de su TextEditingController y lo descarta en su propio
// dispose(). Descartarlo desde quien abre el diálogo, justo al cerrarse, rompe la animación de salida (el
// TextField todavía se construye con un controlador ya descartado).
class _DudaDialog extends StatefulWidget {
  final Future<void> Function(String texto) enviar;

  const _DudaDialog({required this.enviar});

  @override
  State<_DudaDialog> createState() => _DudaDialogState();
}

class _DudaDialogState extends State<_DudaDialog> {
  final _texto = TextEditingController();
  String? _error;
  bool _enviando = false;

  @override
  void dispose() {
    _texto.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    if (_texto.text.trim().isEmpty) {
      setState(() => _error = 'Escribe tu duda.');
      return;
    }
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await widget.enviar(_texto.text);
      if (mounted) Navigator.of(context).pop(true);
    } catch (err) {
      if (!mounted) return;
      setState(() {
        _enviando = false;
        _error = err is ApiException ? err.message : 'No se pudo enviar tu duda.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Tengo una duda'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Solo la administración ve tu duda. Si la respuesta le sirve a todos, la puede publicar como aclaración, sin tu nombre.',
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('duda_texto_field'),
              controller: _texto,
              maxLength: 500,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Escribe tu duda'),
            ),
            if (_error != null)
              Text(
                _error!,
                key: const Key('error_duda'),
                style: const TextStyle(color: Colors.red),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: _enviando ? null : () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
        ElevatedButton(onPressed: _enviando ? null : _enviar, child: Text(_enviando ? 'Enviando…' : 'Enviar')),
      ],
    );
  }
}
