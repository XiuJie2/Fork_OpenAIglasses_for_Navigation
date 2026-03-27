// lib/services/gps_navigation_service.dart
// GPS 導航服務：背景監測與目的地距離，到達時自動結束
// 配合 Google Maps 背景語音導航 + 前景避障模式使用

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';

/// GPS 導航狀態
enum GpsNavState {
  idle,        // 未導航
  navigating,  // 導航中
  arriving,    // 即將到達（< 50m）
  arrived,     // 已到達（< 20m）
}

/// GPS 導航狀態變更回呼
typedef GpsNavCallback = void Function(GpsNavState state, double distanceMeters);

class GpsNavigationService {
  GpsNavigationService._();
  static final instance = GpsNavigationService._();

  // ── 目的地 ──────────────────────────────────────────────────────────────
  double _destLat = 0;
  double _destLng = 0;
  String _destName = '';

  // ── 狀態 ────────────────────────────────────────────────────────────────
  GpsNavState _state = GpsNavState.idle;
  GpsNavState get state => _state;
  double _lastDistance = double.infinity;
  double get lastDistance => _lastDistance;
  String get destName => _destName;

  // ── 監聽 ────────────────────────────────────────────────────────────────
  StreamSubscription<Position>? _positionSub;
  GpsNavCallback? _onStateChanged;
  Timer? _timeoutTimer;

  /// 啟動 GPS 導航
  /// 1. 開啟 Google Maps 背景步行導航（Intent 帶座標，自動開始）
  /// 2. 啟動 GPS 位置監測，持續計算與目的地距離
  Future<bool> startNavigation({
    required double latitude,
    required double longitude,
    required String name,
    required GpsNavCallback onStateChanged,
  }) async {
    // 座標有效性檢查
    if (latitude == 0 && longitude == 0) {
      debugPrint('[GPS] 目的地座標無效，無法啟動導航');
      return false;
    }

    _destLat = latitude;
    _destLng = longitude;
    _destName = name;
    _onStateChanged = onStateChanged;
    _state = GpsNavState.navigating;
    _lastDistance = double.infinity;

    // ── 啟動 Google Maps 步行導航（背景）──
    final gmapsUrl = Uri.parse(
      'google.navigation:q=$latitude,$longitude&mode=w',
    );
    try {
      final launched = await launchUrl(
        gmapsUrl,
        mode: LaunchMode.externalApplication,
      );
      if (!launched) {
        // Google Maps 未安裝，改用瀏覽器版
        final webUrl = Uri.parse(
          'https://www.google.com/maps/dir/?api=1&destination=$latitude,$longitude&travelmode=walking',
        );
        await launchUrl(webUrl, mode: LaunchMode.externalApplication);
      }
      debugPrint('[GPS] Google Maps 步行導航已啟動: $name ($latitude, $longitude)');
    } catch (e) {
      debugPrint('[GPS] 啟動 Google Maps 失敗: $e');
    }

    // ── 啟動 GPS 位置監測 ──
    try {
      _positionSub = Geolocator.getPositionStream(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 5, // 移動 5 公尺才觸發更新（省電）
        ),
      ).listen(_onPositionUpdate, onError: (e) {
        debugPrint('[GPS] 位置串流錯誤: $e');
      });

      // 安全逾時：4 小時自動結束（防止忘記關閉）
      _timeoutTimer = Timer(const Duration(hours: 4), () {
        debugPrint('[GPS] 導航逾時自動結束');
        stopNavigation();
      });

      debugPrint('[GPS] GPS 位置監測已啟動');
      return true;
    } catch (e) {
      debugPrint('[GPS] 啟動位置監測失敗: $e');
      return false;
    }
  }

  /// GPS 位置更新回呼
  void _onPositionUpdate(Position position) {
    if (_state == GpsNavState.idle) return;

    // 計算與目的地的距離（公尺）
    _lastDistance = Geolocator.distanceBetween(
      position.latitude, position.longitude,
      _destLat, _destLng,
    );

    debugPrint('[GPS] 距離 $_destName: ${_lastDistance.toStringAsFixed(0)}m');

    // 狀態轉換
    final prevState = _state;
    if (_lastDistance < 20) {
      _state = GpsNavState.arrived;
    } else if (_lastDistance < 50) {
      _state = GpsNavState.arriving;
    } else {
      _state = GpsNavState.navigating;
    }

    // 狀態有變或距離更新時通知
    if (_state != prevState || _state == GpsNavState.navigating) {
      _onStateChanged?.call(_state, _lastDistance);
    }

    // 到達後自動停止監測（延遲 3 秒讓語音播完）
    if (_state == GpsNavState.arrived) {
      Future.delayed(const Duration(seconds: 3), () {
        if (_state == GpsNavState.arrived) {
          stopNavigation();
        }
      });
    }
  }

  /// 停止 GPS 導航
  void stopNavigation() {
    _positionSub?.cancel();
    _positionSub = null;
    _timeoutTimer?.cancel();
    _timeoutTimer = null;
    _state = GpsNavState.idle;
    _lastDistance = double.infinity;
    debugPrint('[GPS] GPS 導航已停止');
  }

  /// 取得目前位置（單次）
  static Future<Position?> getCurrentPosition() async {
    try {
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
        ),
      );
    } catch (e) {
      debugPrint('[GPS] 取得位置失敗: $e');
      return null;
    }
  }
}
