import 'dart:typed_data';

import 'api_client.dart';

class ReceiptService {
  final ApiClient _api;

  ReceiptService({ApiClient? api}) : _api = api ?? ApiClient();

  Future<Uint8List> descargarRecibo(String paymentId, String token) {
    return _api.getBytes('/payments/$paymentId/receipt', token: token);
  }
}
