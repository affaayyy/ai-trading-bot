import 'package:flutter/material.dart';
import 'api_client.dart';

class PortfolioScreen extends StatefulWidget {
  const PortfolioScreen({super.key});

  @override
  State<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends State<PortfolioScreen> {
  late Future<Map<String, dynamic>> data;

  @override
  void initState() {
    super.initState();
    data = ApiClient.getJson('/api/mobile/portfolio');
  }

  Future<void> refresh() async {
    setState(() => data = ApiClient.getJson('/api/mobile/portfolio'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Portfolio')),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: data,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snapshot.hasError) return ListView(children: [Padding(padding: const EdgeInsets.all(16), child: Text('${snapshot.error}'))]);
            final d = snapshot.data ?? {};
            final holdings = (d['holdings'] as List?) ?? [];
            return ListView(
              padding: const EdgeInsets.all(12),
              children: [
                Card(child: ListTile(title: const Text('Total P&L'), trailing: Text('₹${d['total_pnl'] ?? 0}', style: const TextStyle(fontWeight: FontWeight.bold)))),
                Card(child: ListTile(title: const Text('Current Value'), trailing: Text('₹${d['current_value'] ?? 0}'))),
                const SizedBox(height: 12),
                ...holdings.map((h) {
                  final item = h as Map<String, dynamic>;
                  return Card(child: ListTile(
                    title: Text('${item['symbol']}'),
                    subtitle: Text('Qty ${item['quantity']} | Avg ₹${item['average_price']} | LTP ₹${item['last_price']}'),
                    trailing: Text('₹${item['pnl']}'),
                  ));
                }),
              ],
            );
          },
        ),
      ),
    );
  }
}
