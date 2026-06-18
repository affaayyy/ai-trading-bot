import 'package:flutter/material.dart';
import 'api_client.dart';

class VoiceScreen extends StatefulWidget {
  const VoiceScreen({super.key});

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> {
  final controller = TextEditingController();
  String response = 'Type a voice-style command, for example: Run scanner';
  bool loading = false;

  Future<void> sendCommand() async {
    if (controller.text.trim().isEmpty) return;
    setState(() => loading = true);
    try {
      final result = await ApiClient.postJson('/api/mobile/voice-command', {'command': controller.text.trim()});
      setState(() => response = '${result['response']}');
    } catch (e) {
      setState(() => response = '$e');
    } finally {
      setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Voice Assistant')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Command',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: loading ? null : sendCommand,
              icon: const Icon(Icons.send),
              label: Text(loading ? 'Processing...' : 'Send Command'),
            ),
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(response),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
