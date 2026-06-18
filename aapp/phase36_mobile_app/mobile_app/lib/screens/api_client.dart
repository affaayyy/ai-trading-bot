import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  // Replace with your Render URL, example:
  // static const String baseUrl = 'https://your-app.onrender.com';
  static const String baseUrl = 'https://YOUR_RENDER_URL.onrender.com';

  static Future<Map<String, dynamic>> getJson(String path) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await http.get(uri).timeout(const Duration(seconds: 20));
    if (response.statusCode >= 400) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> postJson(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    ).timeout(const Duration(seconds: 20));
    if (response.statusCode >= 400) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
