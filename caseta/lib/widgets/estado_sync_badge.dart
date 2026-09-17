import 'package:flutter/material.dart';

// Compartido entre AccessLogScreen e IncidentScreen (F2-07): ambas colas
// locales usan el mismo vocabulario de estado (pending/synced/failed).
class EstadoSyncBadge extends StatelessWidget {
  final String estado;
  const EstadoSyncBadge({super.key, required this.estado});

  @override
  Widget build(BuildContext context) {
    final Color color;
    final String etiqueta;
    switch (estado) {
      case 'synced':
        color = Colors.green;
        etiqueta = 'Sincronizado';
      case 'failed':
        color = Colors.red;
        etiqueta = 'Conflicto';
      default:
        color = Colors.orange;
        etiqueta = 'Pendiente';
    }
    return Chip(label: Text(etiqueta), backgroundColor: color.withValues(alpha: 0.15), labelStyle: TextStyle(color: color));
  }
}
