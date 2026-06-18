import 'package:flutter/material.dart';
import 'api_client.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<Map<String, dynamic>> data;

  @override
  void initState() {
    super.initState();
    data = ApiClient.getJson('/api/mobile/dashboard');
  }

  Future<void> refresh() async {
    setState(() => data = ApiClient.getJson('/api/mobile/dashboard'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI Trading Dashboard')),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: data,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(16), child: Text('${snapshot.error}'))]);
            }
            final d = snapshot.data ?? {};
            final cards = [
              ['Capital', '₹${d['capital'] ?? 0}'],
              ['Open Exposure', '₹${d['open_exposure'] ?? 0}'],
              ['Today P&L', '₹${d['today_pnl'] ?? 0}'],
              ['Watchlist', '${d['watchlist_count'] ?? 0} stocks'],
              ['Risk Status', '${d['risk_status'] ?? 'OK'}'],
            ];
            return ListView(
              padding: const EdgeInsets.all(16),
              children: cards.map((item) => Card(
                child: ListTile(title: Text(item[0]), trailing: Text(item[1], style: const TextStyle(fontWeight: FontWeight.bold))),
              )).toList(),
            );
          },
        ),
      ),
    );
  }
}
