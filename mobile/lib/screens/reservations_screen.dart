import 'package:flutter/material.dart';

import '../models/amenity.dart';
import '../models/reservation.dart';
import '../services/amenity_service.dart';
import '../services/api_client.dart';
import '../services/reservation_service.dart';
import '../utils/dates.dart';
import '../utils/labels.dart';

class ReservationsScreen extends StatefulWidget {
  final String token;
  final AmenityService amenityService;
  final ReservationService reservationService;

  const ReservationsScreen({
    super.key,
    required this.token,
    required this.amenityService,
    required this.reservationService,
  });

  @override
  State<ReservationsScreen> createState() => _ReservationsScreenState();
}

class _ReservationsScreenState extends State<ReservationsScreen> {
  List<Amenity>? _amenidades;
  List<Reservation>? _misReservaciones;
  String? _error;
  bool _cargando = true;

  Amenity? _amenidadSeleccionada;
  DateTime? _inicio;
  DateTime? _fin;
  bool _solicitando = false;
  String? _errorSolicitar;

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
      final resultados = await Future.wait([
        widget.amenityService.listarAmenidades(widget.token),
        widget.reservationService.listarMisReservaciones(widget.token),
      ]);
      if (!mounted) return;
      setState(() {
        _amenidades = resultados[0] as List<Amenity>;
        _misReservaciones = resultados[1] as List<Reservation>;
        _amenidadSeleccionada ??= _amenidades!.isNotEmpty ? _amenidades!.first : null;
      });
    } catch (err) {
      if (!mounted) return;
      setState(() => _error = err is ApiException ? err.message : 'No se pudo cargar la información.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _elegirFechaHora({required bool esInicio}) async {
    final ahora = DateTime.now();
    final fecha = await showDatePicker(
      context: context,
      initialDate: ahora,
      firstDate: ahora,
      lastDate: DateTime(ahora.year + 1),
    );
    if (fecha == null || !mounted) return;
    final hora = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(ahora));
    if (hora == null) return;
    final elegido = DateTime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute);
    setState(() {
      if (esInicio) {
        _inicio = elegido;
      } else {
        _fin = elegido;
      }
    });
  }

  Future<void> _solicitar() async {
    final amenidad = _amenidadSeleccionada;
    if (amenidad == null || _inicio == null || _fin == null) return;
    setState(() {
      _solicitando = true;
      _errorSolicitar = null;
    });
    try {
      await widget.reservationService.solicitarReservacion(
        amenityId: amenidad.id,
        fechaInicio: _inicio!,
        fechaFin: _fin!,
        token: widget.token,
      );
      setState(() {
        _inicio = null;
        _fin = null;
      });
      await _cargar();
    } catch (err) {
      if (!mounted) return;
      setState(() => _errorSolicitar = err is ApiException ? err.message : 'No se pudo solicitar la reservación.');
    } finally {
      if (mounted) setState(() => _solicitando = false);
    }
  }

  static String _pad(int n) => n.toString().padLeft(2, '0');

  String _formatoFechaHora(DateTime fecha) {
    final local = fecha.toLocal();
    return '${formatoFechaCorta(local)} ${_pad(local.hour)}:${_pad(local.minute)}';
  }

  // Sin Scaffold/AppBar propios: ver la nota en announcements_screen.dart.
  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(onRefresh: _cargar, child: _buildBody());
  }

  Widget _buildBody() {
    if (_cargando && _amenidades == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _amenidades == null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        ],
      );
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildFormularioSolicitar(),
        const SizedBox(height: 24),
        Text('Mis reservaciones', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        ..._buildMisReservaciones(),
      ],
    );
  }

  Widget _buildFormularioSolicitar() {
    final amenidades = _amenidades ?? [];
    if (amenidades.isEmpty) {
      return const Card(
        child: Padding(padding: EdgeInsets.all(16), child: Text('Todavía no hay amenidades configuradas.')),
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Solicitar reservación'),
            const SizedBox(height: 8),
            DropdownButton<Amenity>(
              key: const Key('amenidad_dropdown'),
              value: _amenidadSeleccionada,
              items: amenidades.map((a) => DropdownMenuItem(value: a, child: Text(a.nombre))).toList(),
              onChanged: (valor) => setState(() => _amenidadSeleccionada = valor),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _elegirFechaHora(esInicio: true),
                    child: Text(_inicio == null ? 'Inicio' : _formatoFechaHora(_inicio!)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _elegirFechaHora(esInicio: false),
                    child: Text(_fin == null ? 'Fin' : _formatoFechaHora(_fin!)),
                  ),
                ),
              ],
            ),
            if (_errorSolicitar != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_errorSolicitar!, style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: (_solicitando || _inicio == null || _fin == null) ? null : _solicitar,
              child: Text(_solicitando ? 'Solicitando…' : 'Solicitar'),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildMisReservaciones() {
    final reservaciones = _misReservaciones ?? [];
    if (reservaciones.isEmpty) {
      return [const Text('Todavía no tienes reservaciones.')];
    }
    return reservaciones
        .map(
          (r) => ListTile(
            title: Text(_formatoFechaHora(r.fechaInicio)),
            subtitle: Text(etiquetasEstadoReserva[r.estado] ?? r.estado),

          ),
        )
        .toList();
  }
}
