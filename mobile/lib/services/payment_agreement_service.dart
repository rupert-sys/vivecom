import '../models/payment_agreement.dart';
import 'api_client.dart';

class PaymentAgreementService {
  final ApiClient _api;

  PaymentAgreementService({ApiClient? api}) : _api = api ?? ApiClient();

  // Los acuerdos de la propia vivienda (el backend ya filtra): los abiertos primero.
  Future<List<PaymentAgreement>> listarMisAcuerdos(String token) async {
    final data = await _api.get('/payment-agreements', token: token) as List;
    return data.map((e) => PaymentAgreement.fromJson(e as Map<String, dynamic>)).toList();
  }

  // El escrito o documento de respaldo (foto o PDF, kind=acuerdo). Regresa el id del archivo.
  Future<String> subirDocumento(List<int> bytes, String nombre, String token) async {
    final data = await _api.postMultipart(
      '/files',
      fields: {'kind': 'acuerdo'},
      fileField: 'file',
      bytes: bytes,
      filename: nombre,
      token: token,
    );
    return (data as Map<String, dynamic>)['id'] as String;
  }

  Future<PaymentAgreement> solicitar({
    required String causa,
    required int numeroDePagos,
    required DateTime primerPago,
    String? archivoId,
    required String token,
  }) async {
    final data = await _api.post('/payment-agreements', {
      'causa': causa.trim(),
      'numero_de_pagos': numeroDePagos,
      'primer_pago': primerPago.toIso8601String().split('T').first,
      'archivo_id': ?archivoId,
    }, token: token);
    return PaymentAgreement.fromJson(data as Map<String, dynamic>);
  }

  // El residente retira su solicitud pendiente (un acuerdo vigente solo lo cancela el comité).
  Future<PaymentAgreement> retirarSolicitud(String agreementId, String token) async {
    final data = await _api.post('/payment-agreements/$agreementId/cancel', {}, token: token);
    return PaymentAgreement.fromJson(data as Map<String, dynamic>);
  }
}
