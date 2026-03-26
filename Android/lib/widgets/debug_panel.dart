// lib/widgets/debug_panel.dart
// 開發者 DEBUG 浮動面板
//   • 平時：右側邊緣顯示一條小 tab（半透明）
//   • 向左滑 tab / 點擊 tab → 面板從右滑入展開
//   • 向右滑面板 → 收起
//   • 透過 OverlayEntry 插入，跨所有子頁面持續顯示

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../core/constants.dart';

class DebugFloatingPanel extends StatefulWidget {
  const DebugFloatingPanel({super.key});

  @override
  State<DebugFloatingPanel> createState() => _DebugFloatingPanelState();
}

class _DebugFloatingPanelState extends State<DebugFloatingPanel>
    with SingleTickerProviderStateMixin {
  bool _open = false;
  late AnimationController _animCtrl;
  late Animation<Offset>   _slideAnim;
  final _scrollCtrl = ScrollController();

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 280),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(1.0, 0),
      end:   Offset.zero,
    ).animate(CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut));
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _open_()  { setState(() => _open = true);  _animCtrl.forward(); }
  void _close_() { setState(() => _open = false); _animCtrl.reverse(); }

  // 自動捲到最新訊息
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 150),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (_, app, __) {
        // 訊息更新時捲到底
        if (_open) _scrollToBottom();

        final panelW = MediaQuery.of(context).size.width * 0.78;

        return Stack(
          children: [

            // ── 背景遮罩（展開時，點擊關閉）──────────────────────────
            if (_open)
              Positioned.fill(
                child: GestureDetector(
                  onTap: _close_,
                  behavior: HitTestBehavior.opaque,
                  child: Container(color: Colors.black.withAlpha(80)),
                ),
              ),

            // ── 收合時的 tab 把手 ─────────────────────────────────────
            if (!_open || _animCtrl.isAnimating)
              Positioned(
                right:  0,
                top:    MediaQuery.of(context).size.height * 0.30,
                child: GestureDetector(
                  onTap: _open_,
                  // 向左滑動（負速度）展開
                  onHorizontalDragEnd: (d) {
                    if ((d.primaryVelocity ?? 0) < -150) _open_();
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width:  28,
                    height: 80,
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFB300).withAlpha(210),
                      borderRadius: const BorderRadius.horizontal(
                          left: Radius.circular(10)),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withAlpha(80),
                          blurRadius: 6,
                          offset: const Offset(-2, 0),
                        ),
                      ],
                    ),
                    child: const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.bug_report,
                            size: 18, color: Colors.black87),
                        SizedBox(height: 4),
                        RotatedBox(
                          quarterTurns: 1,
                          child: Text('DEBUG',
                              style: TextStyle(
                                  fontSize: 8,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.black87,
                                  letterSpacing: 0.5)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

            // ── 展開面板（從右側滑入）────────────────────────────────
            if (_open || _animCtrl.isAnimating)
              Positioned(
                right: 0, top: 0, bottom: 0,
                width: panelW,
                child: SlideTransition(
                  position: _slideAnim,
                  child: GestureDetector(
                    // 向右滑收起
                    onHorizontalDragEnd: (d) {
                      if ((d.primaryVelocity ?? 0) > 200) _close_();
                    },
                    child: _PanelContent(
                      app:        app,
                      scrollCtrl: _scrollCtrl,
                      onClose:    _close_,
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

// ── 面板內容 ──────────────────────────────────────────────────────────────────
class _PanelContent extends StatelessWidget {
  final AppProvider    app;
  final ScrollController scrollCtrl;
  final VoidCallback   onClose;

  const _PanelContent({
    required this.app,
    required this.scrollCtrl,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final serverUrl = app.baseUrl.isNotEmpty
        ? app.baseUrl
        : '${app.host}:${app.port}';

    return Container(
      color: Colors.black.withAlpha(245),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [

            // ── 標題列 ─────────────────────────────────────────────
            Container(
              color: const Color(0xFFFFB300),
              padding: const EdgeInsets.symmetric(
                  vertical: 10, horizontal: 14),
              child: Row(
                children: [
                  const Icon(Icons.bug_report,
                      size: 18, color: Colors.black),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text('DEBUG',
                        style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.black)),
                  ),
                  const Text('← 右滑收起',
                      style: TextStyle(
                          fontSize: 10, color: Colors.black54)),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: onClose,
                    child: const Icon(Icons.close,
                        size: 20, color: Colors.black87),
                  ),
                ],
              ),
            ),

            // ── 系統狀態 ───────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
              child: Column(
                children: [
                  _Row('伺服器',   serverUrl,
                      color: app.connected
                          ? Colors.greenAccent : Colors.redAccent),
                  _Row('連線',     app.connected ? '已連線 ✓' : '未連線 ✗',
                      color: app.connected
                          ? Colors.greenAccent : Colors.redAccent),
                  _Row('導航狀態', app.navState),
                  _Row('狀態標籤', app.navStateLabel),
                  _Row('麥克風',
                      app.isRecordingMic ? '錄音中 ●' : '未啟動',
                      color: app.isRecordingMic
                          ? Colors.greenAccent : Colors.white38),
                  _Row('TTS',
                      app.ttsEnabled ? '已開啟' : '已關閉',
                      color: app.ttsEnabled
                          ? Colors.greenAccent : Colors.white38),
                ],
              ),
            ),

            const Divider(color: Colors.white12, height: 1),

            // ── 訊息記錄標題 ───────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: Row(
                children: [
                  const Text('訊息記錄',
                      style: TextStyle(
                          fontSize: 11,
                          color: Colors.amber,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1)),
                  const Spacer(),
                  Text('${app.messages.length} 筆',
                      style: const TextStyle(
                          fontSize: 10, color: Colors.white30)),
                ],
              ),
            ),

            // ── 訊息清單（最新在最下）──────────────────────────────
            Expanded(
              child: ListView.builder(
                controller:  scrollCtrl,
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                itemCount:   app.messages.length,
                itemBuilder: (_, i) {
                  final msg = app.messages[i];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 1.5),
                    child: Text(
                      msg,
                      style: TextStyle(
                        fontSize:   10.5,
                        color:      _msgColor(msg),
                        fontFamily: 'monospace',
                      ),
                    ),
                  );
                },
              ),
            ),

            // ── API 端點 ───────────────────────────────────────────
            Container(
              color: Colors.white.withAlpha(8),
              padding: const EdgeInsets.all(8),
              child: Text(
                'API: ${AppConstants.httpBase(app.host, app.port, secure: app.secure, baseUrl: app.baseUrl.isNotEmpty ? app.baseUrl : null)}',
                style: const TextStyle(
                    fontSize: 9, color: Colors.white30),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _msgColor(String msg) {
    if (msg.contains('[錯誤]')) return Colors.redAccent;
    if (msg.contains('[ASR]') || msg.contains('[USER]')) {
      return Colors.cyanAccent;
    }
    if (msg.contains('[系統]')) return Colors.white70;
    if (msg.contains('[狀態]')) return Colors.greenAccent;
    return Colors.white38;
  }
}

// ── 狀態資訊列 ────────────────────────────────────────────────────────────────
class _Row extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;

  const _Row(this.label, this.value, {this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 68,
            child: Text(label,
                style: const TextStyle(
                    fontSize: 10,
                    color: Colors.white38,
                    fontFamily: 'monospace')),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                  fontSize: 10,
                  color: color ?? Colors.white70,
                  fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }
}
