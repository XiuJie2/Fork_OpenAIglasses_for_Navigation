# generate_voice.py
# 批量生成預錄語音 WAV 檔 → voice/ 目錄
# 優先使用 Google Cloud TTS Chirp3-HD Sulafat（試用金），失敗時降級到 Gemini TTS（API Key 備用）
# 執行：uv run python generate_voice.py [--force]

import os
import sys
import json
import wave
import time
import base64
import urllib.request
import urllib.error
import numpy as np
from dotenv import load_dotenv

load_dotenv()

VOICE_DIR = os.path.join(os.path.dirname(__file__), "voice")
MAP_FILE = os.path.join(VOICE_DIR, "map.zh-CN.json")
TARGET_SR = 8000

# ── Google Cloud TTS 設定（主力，使用試用金）─────────────────────────────────
GOOGLE_CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "google_Speech_to_Text.json"),
)

# ── Gemini TTS 設定（備用，使用免費 API Key）──────────────────────────────────
_TTS_MODEL = "gemini-2.5-flash-preview-tts"
_TTS_VOICE = "Sulafat"  # 節奏自然的女聲
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

_GEMINI_KEYS = [k for k in [
    os.getenv(f"GEMINI_API_KEY{'_' + str(i) if i > 1 else ''}", "")
    for i in range(1, 17)
] if k]

_key_index = 0


def _next_key() -> str:
    global _key_index
    _key_index = (_key_index + 1) % len(_GEMINI_KEYS)
    return _GEMINI_KEYS[_key_index]


def _current_key() -> str:
    return _GEMINI_KEYS[_key_index]


# ═══════════════════════════════════════════════════════════════════════════════
# 需要生成的語音清單
# ═══════════════════════════════════════════════════════════════════════════════

PHRASES = [
    # ── 盲道導航 ──
    "盲道導航已開始。",
    "過馬路模式已啟動。",
    "已停止導航。",
    "啟動過馬路模式失敗，請稍後重試。",
    "此地已確認沒有盲道，目前只作避障處理。",
    "已回到盲道。",
    "避讓完成，已回到盲道。",
    "丟失路徑，重新搜索。",
    "保持直行。",
    "保持直行，靠近盲道。",
    "切換到盲道導航。",
    "到達轉彎處，向右平移。",
    "到達轉彎處，向左平移。",
    "遠處有盲道，繼續前行。",
    "盲道已接近，開始對準盲道。",
    "方向正確，請直行。",
    "方向正確，請繼續前進。",
    "請向右平移。",
    "請向左平移。",
    "請向右微調，對準盲道。",
    "請向左微調，對準盲道。",
    "向右平移。",
    "向左平移。",
    "稍微向右調整，繼續前進。",
    "稍微向左調整，繼續前進。",
    "前方有右轉彎，繼續直行。",
    "前方有左轉彎，繼續直行。",

    # ── 過馬路 ──
    "遠處發現斑馬線，繼續直行。",
    "發現斑馬線，對準方向。",
    "斑馬線已對準，繼續前行。",
    "正在接近斑馬線，為您對準方向。",
    "正在等待綠燈。",
    "綠燈穩定，開始通行！",
    "綠燈快沒了！",
    "過馬路結束，準備上人行道。",
    "路徑被擋住，請向右側平移。",
    "路徑被擋住，請向左側平移。",

    # ── 其他功能 ──
    "尋物任務完成。",
    "導航已被取消。",
    "歡迎使用AI智慧眼鏡！",
    "開始對話。",
    "結束收音。",
]


def _strip_punctuation(text: str) -> str:
    """移除句尾標點，用於檔名和 map key"""
    return text.rstrip("。！？!?.，,")


# ── 主力：Google Cloud TTS Chirp3-HD（試用金）─────────────────────────────────

def _chirp3_tts(text: str) -> bytes | None:
    """
    Google Cloud TTS Chirp3-HD Sulafat → PCM16 24kHz bytes。
    使用服務帳號憑證，消耗 Google Cloud 試用金。
    """
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="cmn-CN",
                name="cmn-CN-Chirp3-HD-Sulafat",
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000,
            ),
        )
        # response.audio_content 為含 WAV header 的 bytes，跳過 44-byte header 取 PCM
        return response.audio_content[44:]
    except Exception as e:
        print(f" [Chirp3-HD 失敗: {e}]", end="")
        return None


# ── 備用：Gemini TTS（免費 API Key）──────────────────────────────────────────

def _gemini_tts(text: str, retries: int = 3) -> bytes | None:
    """呼叫 Gemini TTS（備用），回傳 PCM16 24kHz bytes"""
    if not _GEMINI_KEYS:
        print(" [無 Gemini Key]", end="")
        return None

    # 加上風格指令，讓語氣明亮親切
    styled = f"用明亮、親切的語氣說：{text}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": styled}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": _TTS_VOICE}}
            },
        },
    }).encode()

    for attempt in range(retries):
        key = _current_key()
        url = f"{_BASE_URL}/{_TTS_MODEL}:generateContent?key={key}"
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            cand = result.get("candidates", [{}])[0]
            if "content" not in cand:
                reason = cand.get("finishReason", "?")
                print(f" [Gemini TTS 無音訊: {reason}]", end="")
                return None
            data = cand["content"]["parts"][0].get("inlineData", {}).get("data", "")
            return base64.b64decode(data) if data else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f" [429→換Key]", end="")
                _next_key()
                time.sleep(2)
                continue
            print(f" [HTTP {e.code}]", end="")
            return None
        except Exception as e:
            print(f" [Gemini 錯誤: {e}]", end="")
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return None
    return None


def _synthesize(text: str) -> bytes | None:
    """
    合成語音：Google Cloud WaveNet（試用金）優先，失敗降級到 Gemini TTS（API Key 備用）。
    """
    # ① 主力：Google Cloud TTS Chirp3-HD（試用金）
    pcm = _chirp3_tts(text)
    if pcm:
        return pcm

    # ② 備用：Gemini TTS
    print(" → 降級到 Gemini TTS", end="")
    return _gemini_tts(text)


def _resample_to_8k(pcm_24k: bytes) -> bytes:
    """24kHz PCM16 → 8kHz PCM16（線性插值）"""
    samples = np.frombuffer(pcm_24k, dtype=np.int16).astype(np.float64)
    n_out = int(len(samples) * TARGET_SR / 24000)
    x_old = np.linspace(0, 1, len(samples))
    x_new = np.linspace(0, 1, n_out)
    resampled = np.interp(x_new, x_old, samples)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


def save_wav(path: str, pcm_data: bytes, sample_rate: int = TARGET_SR):
    """寫入標準 WAV 檔"""
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


def main():
    # 載入現有 map
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        voice_map = json.load(f)

    print("═" * 60)
    print("語音生成策略：Google Cloud TTS Chirp3-HD Sulafat（試用金）優先")
    print("             Gemini TTS（API Key）備用")
    print(f"可用 Gemini API Key：{len(_GEMINI_KEYS)} 組")
    print("═" * 60 + "\n")

    generated = 0
    skipped = 0
    failed = 0

    for phrase in PHRASES:
        clean = _strip_punctuation(phrase)
        fname = f"{clean}.wav"
        fpath = os.path.join(VOICE_DIR, fname)

        # 已有檔案 → 跳過（加 --force 強制重新生成）
        if "--force" not in sys.argv and os.path.exists(fpath) and os.path.getsize(fpath) > 500:
            print(f"  [跳過] {clean}（已存在）")
            skipped += 1
            continue

        print(f"  [生成] {clean}...", end="", flush=True)

        pcm_24k = _synthesize(phrase)
        if pcm_24k is None:
            print(" 失敗")
            failed += 1
            continue

        pcm_8k = _resample_to_8k(pcm_24k)
        save_wav(fpath, pcm_8k)
        dur_ms = int(len(pcm_8k) / 2 / TARGET_SR * 1000)

        voice_map[clean] = {"files": [fname], "duration_ms": dur_ms}

        print(f" OK ({dur_ms}ms)")
        generated += 1

        time.sleep(0.3)

    # 寫回 map
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(voice_map, f, ensure_ascii=False, indent=2)

    print(f"\n完成：生成 {generated}，跳過 {skipped}，失敗 {failed}")
    print(f"語音映射已更新：{MAP_FILE}")


if __name__ == "__main__":
    main()
