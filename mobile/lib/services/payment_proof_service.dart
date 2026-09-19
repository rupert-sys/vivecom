import '../models/payment_proof.dart';
import 'api_client.dart';

class PaymentProofService {
  final ApiClient _api;

  PaymentProofService({ApiClient? api}) : _api = api ?? ApiClient();

  // Los comprobantes de la propia vivienda (el backend ya filtra), los recientes primero.
  Future<List<PaymentProof>> listarMisComprobantes(String token) async {
    final data = await _api.get('/payment-proofs', token: token) as List;
    return data.map((e) => PaymentProof.fromJson(e as Map<String, dynamic>)).toList();
  }

  // Sube la foto o el PDF (kind=pago) y regresa el id del archivo.
  Future<String> subirArchivo(List<int> bytes, String nombre, String token) async {
    final data = await _api.postMultipart(
      '/files',
      fields: {'kind': 'pago'},
      fileField: 'file',
      bytes: bytes,
      filename: nombre,
      token: token,
    );
    return (data as Map<String, dynamic>)['id'] as String;
  }

  Future<PaymentProof> enviarComprobante({
    required double monto,
    required String archivoId,
    DateTime? fechaPago,
    String? nota,
    required String token,
  }) async {
    final data = await _api.post('/payment-proofs', {
      'monto': monto,
      'archivo_id': archivoId,
      if (fechaPago != null) 'fecha_pago': fechaPago.toIso8601String().split('T').first,
      if (nota != null && nota.trim().isNotEmpty) 'nota': nota.trim(),
    }, token: token);
    return PaymentProof.fromJson(data as Map<String, dynamic>);
  }
}
