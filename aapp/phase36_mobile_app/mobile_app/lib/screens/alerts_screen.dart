import 'package:flutter/material.dart';
import 'api_client.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  late Future<Map<String, dynamic>> data;

  @override
  void initState() {
    super.initState();
    data = ApiClient.getJson('/api/mobile/alerts');
  }

  Future<void> refresh() async {
    setState(() => data = ApiClient.getJson('/api/mobile/alerts'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI Alerts')),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: data,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snapshot.hasError) return ListView(children: [Padding(padding: const EdgeInsets.all(16), child: Text('${snapshot.error}'))]);
            final alerts = (snapshot.data?['alerts'] as List?) ?? [];
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: alerts.length,
              itemBuilder: (context, index) {
                final item = alerts[index] as Map<String, dynamic>;
                return Card(
                  child: ListTile(
                    title: Text('${item['title']}'),
                    subtitle: Text('${item['message']}'),
                    trailing: Text('${item['time']}'),
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
