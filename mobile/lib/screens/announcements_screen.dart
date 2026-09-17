import 'package:flutter/material.dart';

import '../models/announcement.dart';
import '../services/announcement_service.dart';
import '../services/api_client.dart';
import '../utils/dates.dart';

class AnnouncementsScreen extends StatefulWidget {
  final String token;
  final AnnouncementService announcementService;

  const AnnouncementsScreen({super.key, required this.token, required this.announcementService});

  @override
  State<AnnouncementsScreen> createState() => _AnnouncementsScreenState();
}

class _AnnouncementsScreenState extends State<AnnouncementsScreen> {
  List<Announcement>? _avisos;
  String? _error;
  bool _cargando = true;

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
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudieron cargar los avisos.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _marcarLeido(Announcement aviso) async {
    if (aviso.leido == true) return;
    try {
      await widget.announcementService.marcarLeido(aviso.id, widget.token);
      if (!mounted) return;
      setState(() {
        final indice = _avisos!.indexWhere((a) => a.id == aviso.id);
        if (indice != -1) {
          _avisos![indice] = Announcement(
            id: aviso.id,
            titulo: aviso.titulo,
            contenido: aviso.contenido,
            fechaPublicacion: aviso.fechaPublicacion,
            leido: true,
          );
        }
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
        if (abierto) _marcarLeido(aviso);
      },
      leading: noLeido
          ? const Icon(Icons.circle, size: 10, color: Colors.blue, key: Key('punto_no_leido'))
          : const SizedBox(width: 10),
      title: Text(
        aviso.titulo,
        style: TextStyle(fontWeight: noLeido ? FontWeight.bold : FontWeight.normal),
      ),
      subtitle: Text(formatoFechaCorta(aviso.fechaPublicacion)),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Align(alignment: Alignment.centerLeft, child: Text(aviso.contenido)),
        ),
      ],
    );
  }
}
