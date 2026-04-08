---
allowed-tools: Read, Grep, Bash(python:*), Bash(grep:*)
description: AI 眼鏡專案修改驗證（含 TTS、Vertex AI 專屬測試）
---

在通用 /check 之上，額外執行以下專案特有驗證。

## TTS 改動後必做

```python
# 直接打 API，確認回傳 bytes > 0
import omni_client as oc
pcm = oc._call_tts('前方有斑馬線，請注意。', 'Aoede')
assert pcm and len(pcm) > 0, "Gemini TTS 失敗"

from audio_player import _wavenet_tts
pcm = _wavenet_tts('前方有斑馬線，請注意。')
assert pcm and len(pcm) > 0, "WaveNet TTS 失敗"
```

**TTS 地雷**：
- Gemini TTS 對 ≤4 字短句/問句 → 400（模型限制，非 bug）
- Gemini TTS 不支援 `systemInstruction` → 500
- 短句播報必須走 WaveNet，不能走 Gemini TTS

## Vertex AI 改動後必做

```python
import omni_client as oc
oc._VERTEX_EXHAUSTED = False

# 1. Vertex 正常呼叫
result = oc._call_flash([{'text': '1+1=？只回數字'}], '')
assert result

# 2. 自動切換
oc._mark_vertex_exhausted()
assert not oc._use_vertex()
result = oc._call_flash([{'text': '1+1=？只回數字'}], '')
assert result

# 3. 串流
oc._VERTEX_EXHAUSTED = False
chunks = list(oc._stream_flash_sync([{'text': '說一個顏色'}], ''))
assert chunks
```

## config.py / .env 改動後必做

```bash
.venv/Scripts/python -c "import config; print('OK')"
```

## model_server.py 改動後必做

```python
import asyncio, model_server as ms

ms._models = {'yolo-seg': object(), 'yolo-obs': object(), 'trafficlight': object()}

async def test():
    ms._init_locks()
    locks = ms._inference_locks

    # 1. 每個模型各自有鎖
    for name in ms._models:
        assert name in locks, f'{name} 鎖不存在'

    # 2. 不同模型鎖互相獨立
    assert locks['yolo-seg'] is not locks['yolo-obs'], '鎖不獨立'

    # 3. Skip-if-busy：yolo-seg 忙時 yolo-obs 仍可取得
    async with locks['yolo-seg']:
        assert locks['yolo-seg'].locked()
        assert not locks['yolo-obs'].locked()
        async with locks['yolo-obs']:
            pass  # 可以取得

    print('model_server 測試通過')

asyncio.run(test())
```

## 任何程式碼改動後的通用規則

**改完就測，不等使用者叫。** 每次修改完畢，立即執行對應測試再回報結果。

## commit 前 → 改用 /pre-commit
