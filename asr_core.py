# asr_core.py
# -*- coding: utf-8 -*-
"""
ASR 核心模組：使用 Groq Whisper Large v3 Turbo 進行語音辨識。

架構說明：
- GroqASR 緩衝 PCM16 音訊，每 BUFFER_SEC 秒批次送出一次請求
- 無 partial 中途結果，只有 final（與 DashScope 介面相容）
- ASRCallback 邏輯不變，熱詞觸發與 LLM 驅動流程維持原設計
"""

import os, json, asyncio, io, wave, struct, urllib.request, urllib.error
from typing import Any, Dict, List, Optional, Callable, Tuple

ASR_DEBUG_RAW = os.getenv("ASR_DEBUG_RAW", "0") == "1"

# ── 工具函式 ─────────────────────────────────────────────────────────────────

def _shorten(s: str, limit: int = 200) -> str:
    if not s:
        return ""
    return s if len(s) <= limit else (s[:limit] + "…")

def _normalize_cn(s: str) -> str:
    try:
        import unicodedata
        s = "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in s)
        s = s.strip().lower()
    except Exception:
        s = (s or "").strip().lower()
    return s

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000,
                channels: int = 1, sampwidth: int = 2) -> bytes:
    """將原始 PCM16 資料包裝為 WAV 格式（Groq API 需要）"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()

async def _groq_transcribe(wav_data: bytes, api_key: str) -> Optional[str]:
    """呼叫 Groq Whisper Large v3 Turbo API 轉錄音訊（在執行緒中執行以避免阻塞）"""

    def _do_request() -> Optional[str]:
        boundary = "GASRBoundary7MA4YWxk"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode() + wav_data + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f"whisper-large-v3-turbo\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="language"\r\n\r\n'
            f"zh\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "groq-asr/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read()).get("text", "")
        except urllib.error.HTTPError as e:
            body_err = e.read().decode(errors="replace")
            print(f"[GroqASR] HTTP {e.code}: {body_err}", flush=True)
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _do_request)

# ── 熱詞設定 ─────────────────────────────────────────────────────────────────

INTERRUPT_KEYWORDS = set(
    os.getenv("INTERRUPT_KEYWORDS", "停下所有功能,停止所有功能").split(",")
)

# ── ASR 全局總閘 ─────────────────────────────────────────────────────────────

_current_recognition: Optional[object] = None
_rec_lock = asyncio.Lock()

async def set_current_recognition(r):
    global _current_recognition
    async with _rec_lock:
        _current_recognition = r

async def stop_current_recognition():
    global _current_recognition
    async with _rec_lock:
        r = _current_recognition
        _current_recognition = None
    if r:
        try:
            r.stop()
        except Exception:
            pass

# ── ASRCallback（邏輯不變，相容新的 GroqASR）────────────────────────────────

class ASRCallback:
    """
    設計目標：
    1) 「停下 / 別說了 …」等熱詞一出現 → 立刻全清零重置。
    2) AI 正在播報時，用戶語音只做展示，不觸發新一輪。
    3) 只有 final sentence 用於驅動 AI（Groq 每次結果均為 final）。
    """

    def __init__(
        self,
        on_sdk_error: Callable[[str], None],
        post: Callable[[asyncio.Future], None],
        ui_broadcast_partial,
        ui_broadcast_final,
        is_playing_now_fn: Callable[[], bool],
        start_ai_with_text_fn,
        full_system_reset_fn,
        interrupt_lock: asyncio.Lock,
    ):
        self._on_sdk_error = on_sdk_error
        self._post = post
        self._ui_partial = ui_broadcast_partial
        self._ui_final   = ui_broadcast_final
        self._is_playing = is_playing_now_fn
        self._start_ai   = start_ai_with_text_fn
        self._full_reset = full_system_reset_fn
        self._interrupt_lock = interrupt_lock
        self._hot_interrupted: bool = False

    def on_open(self):  pass
    def on_close(self): pass
    def on_complete(self): pass

    def on_error(self, err):
        try:
            self._post(self._ui_partial(""))
            self._on_sdk_error(str(err))
        except Exception:
            pass

    def on_result(self, result): self._handle(result)
    def on_event(self,  event):  self._handle(event)

    def _has_hotword(self, text: str) -> bool:
        t = _normalize_cn(text)
        if not t:
            return False
        for w in INTERRUPT_KEYWORDS:
            if w and _normalize_cn(w) in t:
                return True
        return False

    def _handle(self, event: Any):
        # 解析事件（相容 GroqASR 產生的 dict 格式）
        if isinstance(event, dict):
            d = event
        else:
            return

        # 向下挖掘 sentence 結構
        text, is_end = None, None
        sentence = (d.get("output") or {}).get("sentence") or d.get("sentence")
        if isinstance(sentence, dict):
            text   = sentence.get("text")
            is_end = sentence.get("sentence_end")
            if is_end is not None:
                is_end = bool(is_end)

        if text is None or not text.strip():
            return
        text = text.strip()

        if ASR_DEBUG_RAW:
            print(f"[ASR EVENT] text='{_shorten(text)}' is_end={is_end}", flush=True)

        # ① 熱詞優先：命中就全清零並短路
        if not self._hot_interrupted and self._has_hotword(text):
            self._hot_interrupted = True

            async def _hot_reset():
                async with self._interrupt_lock:
                    print(f"[ASR HOTWORD] '{text}' -> FULL RESET", flush=True)
                    await self._full_reset("Hotword interrupt")
            try:
                self._post(_hot_reset())
            except Exception:
                pass
            return

        # ② 展示給 UI（Groq 無 partial，直接顯示 final 文字）
        try:
            print(f"[ASR PARTIAL] '{_shorten(text)}'", flush=True)
            self._post(self._ui_partial(text))
        except Exception:
            pass

        # ③ final 驅動 LLM（Groq 每次結果均為 final）
        if is_end is True:
            final_text = text
            try:
                print(f"[ASR FINAL] '{final_text}'", flush=True)
                self._post(self._ui_final(final_text))
            except Exception:
                pass

            if (not self._is_playing()) and final_text:
                async def _run_final():
                    async with self._interrupt_lock:
                        print(f"[LLM INPUT TEXT] {final_text}", flush=True)
                        await self._start_ai(final_text)
                try:
                    self._post(_run_final())
                except Exception:
                    pass

            self._hot_interrupted = False

# ── GroqASR：替代 DashScope Recognition ─────────────────────────────────────

class GroqASR:
    """
    使用 Groq Whisper Large v3 Turbo 的批次 ASR。
    介面與 DashScope Recognition 相容：start() / stop() / send_audio_frame()

    每 BUFFER_SEC 秒將緩衝的 PCM16 音訊打包成 WAV 送出轉錄，
    結果以 final sentence 形式傳入 ASRCallback。
    """

    BUFFER_SEC: float = 4.0   # 每次送出的緩衝秒數（加大以避免長句被切斷）

    def __init__(self, api_key: str, sample_rate: int, callback: ASRCallback):
        self._api_key     = api_key
        self._sample_rate = sample_rate
        self._callback    = callback
        self._buffer      = bytearray()
        self._running     = False
        self._flush_task: Optional[asyncio.Task] = None
        # 最短有效音訊長度（避免送出純靜音）：0.8 秒
        self._min_bytes   = int(sample_rate * 2 * 0.8)

    def start(self):
        """啟動緩衝與定期轉錄任務"""
        self._running = True
        self._buffer.clear()
        loop = asyncio.get_event_loop()
        self._flush_task = loop.create_task(self._flush_loop())
        print("[GroqASR] started", flush=True)

    def stop(self):
        """停止並刷出剩餘緩衝音訊"""
        self._running = False
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        remaining = bytes(self._buffer)
        self._buffer.clear()
        if len(remaining) >= self._min_bytes:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self._transcribe_and_dispatch(remaining))
            except Exception:
                pass
        print("[GroqASR] stopped", flush=True)

    def send_audio_frame(self, data: bytes):
        """接收音訊幀並累積至緩衝區"""
        if self._running:
            self._buffer.extend(data)

    async def _flush_loop(self):
        """背景迴圈：每 BUFFER_SEC 秒送出一次轉錄請求"""
        try:
            while self._running:
                await asyncio.sleep(self.BUFFER_SEC)
                if not self._running:
                    break
                data = bytes(self._buffer)
                self._buffer.clear()
                if len(data) >= self._min_bytes:
                    await self._transcribe_and_dispatch(data)
        except asyncio.CancelledError:
            pass

    async def _transcribe_and_dispatch(self, pcm_data: bytes):
        """將 PCM 資料轉為 WAV 後送 Groq，結果傳入 callback"""
        try:
            wav_data = _pcm_to_wav(pcm_data, self._sample_rate)
            text = await _groq_transcribe(wav_data, self._api_key)
            if text and text.strip():
                text = text.strip()
                print(f"[GroqASR] result: '{_shorten(text)}'", flush=True)
                event = {
                    "output": {
                        "sentence": {"text": text, "sentence_end": True}
                    }
                }
                self._callback.on_event(event)
        except Exception as e:
            print(f"[GroqASR] error: {e}", flush=True)
            self._callback.on_error(str(e))
