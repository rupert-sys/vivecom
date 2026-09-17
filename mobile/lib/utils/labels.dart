// Etiquetas en español para los enums de estado que regresa el backend
// (EstadoCargo en app/models/fee_charge.py, EstadoPago en
// app/models/payment.py) — compartidas entre pantallas para no duplicar el
// mapeo cada vez que se muestra un cargo o un pago.

const Map<String, String> etiquetasEstadoCargo = {'pendiente': 'Pendiente', 'pagado': 'Pagado', 'vencido': 'Vencido'};

const Map<String, String> etiquetasEstadoPago = {
  'pendiente': 'Pendiente',
  'confirmado': 'Confirmado',
  'rechazado': 'Rechazado',
};
