---
allowed-tools: Read
description: 系統架構、模組職責、Port 對照、TTS 地雷速查
---

## 啟動方式

```bash
uv run python app_main.py                    # 單機 port 8081
uv run python start_multi_device.py         # 多裝置 8081～8084
cd Website && docker compose up --build     # 網站 port 8888
```

## Port 分工

| Port | 用途 |
|------|------|
| 8888 | nginx 網站入口（Docker）|
| 8081～8084 | FastAPI 各裝置 instance |
| 12345 UDP | ESP32 IMU 資料 |

## 核心模組

| 檔案 | 職責 |
|------|------|
| `app_main.py` | FastAPI 入口、WebSocket 路由、模型初始化 |
| `navigation_master.py` | 全域狀態機、process_frame() 派發 |
| `omni_client.py` | Gemini Flash 串流 + TTS（Vertex AI 優先，AI Studio 備援）|
| `audio_player.py` | 音訊播放、WaveNet TTS fallback |
| `asr_core.py` | Google STT 串流（待機/主動雙模式）|
| `bridge_io.py` | WebSocket ↔ AI 推理執行緒安全緩衝 |

## AI 服務分工

| 功能 | 服務 |
|------|------|
| ASR | Google Speech-to-Text 串流 |
| 語音對話 + 場景描述 | Gemini 2.5 Flash（Vertex AI 優先）|
| 導航 TTS | WaveNet（cmn-TW-Wavenet-A）|
| 對話 TTS | Gemini TTS（gemini-2.5-flash-preview-tts）|
| 盲道/障礙/紅綠燈 | 本地 YOLO 模型 |

## TTS 地雷

- Gemini TTS ≤4 字短句/問句 → 400
- Gemini TTS 不支援 systemInstruction → 500
- **短句播報必須走 WaveNet**

## Vertex AI 備援

`USE_VERTEX_AI=true` → 先走 Vertex，配額耗盡自動切回 AI Studio 16-Key 輪換
