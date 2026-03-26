// lib/screens/emergency_select_screen.dart
// 緊急求救選人畫面：顯示最多兩位聯絡人，視障者選擇後立即撥打

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../services/call_service.dart';

class EmergencySelectScreen extends StatefulWidget {
  const EmergencySelectScreen({super.key});

  @override
  State<EmergencySelectScreen> createState() => _EmergencySelectScreenState();
}

class _EmergencySelectScreenState extends State<EmergencySelectScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final app = context.read<AppProvider>();
      final contacts = app.contacts;
      if (contacts.isEmpty) {
        app.speak('尚未設定緊急連絡人');
        Navigator.pop(context);
        return;
      }
      // TTS 提示
      final names = contacts.map((c) => c['name'] as String).join('或');
      app.speak('請選擇求救對象：$names');
    });
  }

  Future<void> _call(BuildContext ctx, Map<String, dynamic> contact) async {
    HapticFeedback.heavyImpact();
    final phone = contact['phone'] as String? ?? '';
    if (phone.isEmpty) {
      // 按鈕語音已移入 Semantics 標籤（電話未設定），不重複播報
      return;
    }
    // 按鈕語音已移入 Semantics 標籤（點擊立即撥打...），不重複播報
    Navigator.pop(ctx);
    await CallService.call(phone);
  }

  @override
  Widget build(BuildContext context) {
    final contacts = context.watch<AppProvider>().contacts;

    // 顏色：主要=深藍，次要=深橘
    const colors = [Color(0xFF0D47A1), Color(0xFFE65100)];

    return GestureDetector(
      onHorizontalDragEnd: (details) {
        if ((details.primaryVelocity ?? 0) > 300) {
          context.read<AppProvider>().speak('取消，返回上一頁');
          Navigator.pop(context);
        }
      },
      child: Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── 頂部標題 ──────────────────────────────────────────────────
            Container(
              color: const Color(0xFF1A1A1A),
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 20),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      '緊急求救　選擇聯絡人',
                      style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),

            // ── 聯絡人色塊 ────────────────────────────────────────────────
            ...contacts.asMap().entries.map((entry) {
              final i = entry.key;
              final c = entry.value;
              final phone = c['phone'] as String? ?? '';
              return Expanded(
                child: Semantics(
                  label: phone.isEmpty
                      ? '${c['name']}，電話未設定，無法撥打'
                      : '點擊立即撥打電話給${c['name']}，號碼 $phone',
                  button: true,
                  child: GestureDetector(
                    onTap: () => _call(context, c),
                    child: Container(
                      color: colors[i % colors.length],
                      padding: const EdgeInsets.symmetric(
                          vertical: 24, horizontal: 28),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            i == 0 ? '主要聯絡人' : '次要聯絡人',
                            style: const TextStyle(
                                fontSize: 18, color: Colors.white70),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            c['name'] as String,
                            style: const TextStyle(
                                fontSize: 44,
                                fontWeight: FontWeight.bold,
                                color: Colors.white),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            c['phone'] as String,
                            style: const TextStyle(
                                fontSize: 24, color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            }),

            // ── 取消按鈕 ─────────────────────────────────────────────────
            Semantics(
              label: '取消，返回上一頁',
              button: true,
              child: GestureDetector(
              onTap: () {
                HapticFeedback.mediumImpact();
                // 按鈕語音已移入 Semantics 標籤（取消，返回上一頁），不重複播報
                Navigator.pop(context);
              },
              child: Container(
                color: const Color(0xFF212121),
                padding: const EdgeInsets.symmetric(vertical: 22),
                child: const Center(
                  child: Text(
                    '取消',
                    style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Colors.white54),
                  ),
                ),
              ),
            ),
            ),
          ],
        ),
      ),
    ),   // Scaffold
    );   // GestureDetector
  }
}
