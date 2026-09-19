// Ocupación de los cajones de visitas (GET /access-log/estacionamiento-visitas):
// el guardia decide si deja entrar un vehículo más o si el visitado debe tener
// lugar propio (reglamento Art. 2 IX-XI).
class ParkingStatus {
  final int totalCajones;
  final int ocupados;
  final int libres;
  final int horasMaximas;
  final int excedidos; // vehículos que ya rebasaron el tiempo máximo

  ParkingStatus({
    required this.totalCajones,
    required this.ocupados,
    required this.libres,
    required this.horasMaximas,
    required this.excedidos,
  });

  factory ParkingStatus.fromJson(Map<String, dynamic> json) {
    return ParkingStatus(
      totalCajones: json['total_cajones'] as int,
      ocupados: json['ocupados'] as int,
      libres: json['libres'] as int,
      horasMaximas: json['horas_maximas'] as int,
      excedidos: (json['excedidos'] as List).length,
    );
  }
}
