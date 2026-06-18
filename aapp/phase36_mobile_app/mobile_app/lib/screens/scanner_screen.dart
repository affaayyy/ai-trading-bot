import 'package:flutter/material.dart';
import 'api_client.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  late Future<Map<String, dynamic>> data;

  @override
  void initState() {
    super.initState();
    data = ApiClient.getJson('/api/mobile/scanner');
  }

  Future<void> refresh() async {
    setState(() => data = ApiClient.getJson('/api/mobile/scanner'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI Scanner')),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: data,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snapshot.hasError) return ListView(children: [Padding(padding: const EdgeInsets.all(16), child: Text('${snapshot.error}'))]);
            final results = (snapshot.data?['results'] as List?) ?? [];
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: results.length,
              itemBuilder: (context, index) {
                final item = results[index] as Map<String, dynamic>;
                return Card(
                  child: ListTile(
                    title: Text('${item['symbol']}  •  ${item['signal']}'),
                    subtitle: Text('Price ₹${item['current_price']} | RSI ${item['rsi']} | ${item['reasons']}'),
                    trailing: Text('${item['confidence']}%'),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
