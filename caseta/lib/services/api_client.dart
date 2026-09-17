import 'dart:convert';

import 'package:http/http.dart' as http;

// iOS Simulator comparte la red del host, así que localhost apunta al
// backend corriendo en la máquina de desarrollo (uvicorn en :8000). Mismo
// patrón que app_residente (mobile/lib/services/api_client.dart).
const String apiBaseUrl = 'http://localhost:8000';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ApiClient {
  final http.Client _client;
  final String baseUrl;

  ApiClient({http.Client? client, this.baseUrl = apiBaseUrl}) : _client = client ?? http.Client();

  Future<dynamic> get(String path, {String? token}) async {
    final response = await _client.get(Uri.parse('$baseUrl$path'), headers: _headers(token));
    return _handle(response);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body, {String? token}) async {
    final response = await _client.post(
      Uri.parse('$baseUrl$path'),
      headers: {'Content-Type': 'application/json', ..._headers(token)},
      body: jsonEncode(body),
    );
    return _handle(response);
  }

  Map<String, String> _headers(String? token) => {if (token != null) 'Authorization': 'Bearer $token'};

  dynamic _handle(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    throw ApiException(_extraerMensaje(response), statusCode: response.statusCode);
  }

  // Refleja extraerMensajeDeError() del panel admin y de app_residente: el
  // detail de FastAPI puede ser un string (HTTPException) o una lista de
  // objetos (error 422 de validación de Pydantic).
  String _extraerMensaje(http.Response response) {
    try {
      final data = jsonDecode(response.body);
      final detail = data['detail'];
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        final primero = detail.first;
        if (primero is Map && primero['msg'] != null) {
          return primero['msg'].toString();
        }
      }
    } catch (_) {
      // Respuesta sin JSON válido (ej. 502 de un proxy) — cae al mensaje genérico.
    }
    return 'Ocurrió un error inesperado.';
  }
}
