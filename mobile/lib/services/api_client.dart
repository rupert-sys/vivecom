import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

// iOS Simulator comparte la red del host, así que localhost apunta al
// backend corriendo en la máquina de desarrollo (uvicorn en :8000). En un iPhone
// físico localhost es el propio teléfono: se lanza con la IP de la Mac,
// `flutter run --dart-define=API_BASE_URL=http://192.168.1.90:8000`.
const String apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

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

  // Subida de un archivo (multipart/form-data): comprobantes de pago. El Content-Type
  // (con su boundary) lo arma MultipartRequest; el backend valida el tipo por los bytes.
  Future<dynamic> postMultipart(
    String path, {
    required Map<String, String> fields,
    required String fileField,
    required List<int> bytes,
    required String filename,
    String? token,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl$path'))
      ..fields.addAll(fields)
      ..files.add(http.MultipartFile.fromBytes(fileField, bytes, filename: filename))
      ..headers.addAll(_headers(token));
    final response = await http.Response.fromStream(await _client.send(request));
    return _handle(response);
  }

  // Para respuestas binarias (ej. el PDF del recibo de F1-11/F1-27) —
  // apiFetch() del panel admin asume JSON en todo el proyecto y por eso tuvo
  // que agregar downloadFile.ts aparte (F1-23); aquí se resuelve como un
  // método más de ApiClient, reusando el mismo manejo de error JSON.
  Future<Uint8List> getBytes(String path, {String? token}) async {
    final response = await _client.get(Uri.parse('$baseUrl$path'), headers: _headers(token));
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.bodyBytes;
    }
    throw ApiException(_extraerMensaje(response));
  }

  Map<String, String> _headers(String? token) => {if (token != null) 'Authorization': 'Bearer $token'};

  dynamic _handle(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    throw ApiException(_extraerMensaje(response));
  }

  // Refleja extraerMensajeDeError() del panel admin (frontend/src/api/client.ts):
  // el detail de FastAPI puede ser un string (HTTPException) o una lista de
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
