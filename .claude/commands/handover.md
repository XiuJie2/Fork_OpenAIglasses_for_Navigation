---
allowed-tools: Read, Bash(git:*), Bash(python:*)
description: 交接資料更新檢查 + 缺失語音 log 處理
---

## 1. 交接資料更新檢查

```bash
# 查看 _交接資料/ 各檔案的最後修改時間
python -c "
import os, datetime
folder = '_交接資料'
if not os.path.isdir(folder):
    print('_交接資料/ 不存在')
else:
    files = [(f, os.path.getmtime(os.path.join(folder, f))) for f in os.listdir(folder)]
    files.sort(key=lambda x: -x[1])
    for fname, mtime in files:
        dt = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        print(f'{dt}  {fname}')
"
```

比對上次檢查時間，若有新的修改必須告知使用者：
- 哪些檔案更新了
- 更新時間
- 建議使用者確認內容有無異動（API Key 更換、新增帳號等）

---

## 2. 缺失語音 log 處理（`voice_missing_log/`）

### 2a. 拉取部署機 push 的 log
```bash
git pull
ls voice_missing_log/
```

### 2b. 查看缺失清單
```bash
python -c "
import os, json
log_dir = 'voice_missing_log'
with open('voice/map.zh-CN.json', encoding='utf-8') as f:
    m = json.load(f)
existing_keys = set(m.keys())

missing = []
for fname in sorted(os.listdir(log_dir)):
    if not fname.endswith('.txt'):
        continue
    with open(os.path.join(log_dir, fname), encoding='utf-8') as f:
        for line in f:
            t = line.strip().rstrip('。！？!?.，,')
            if t and t not in existing_keys:
                missing.append((fname, t))

print(f'共 {len(missing)} 條缺失語音：')
for date, text in missing:
    print(f'  [{date}] {text}')
"
```

### 2c. 新增到 generate_voice.py 並生成 WAV
1. 將缺失文字加入 `generate_voice.py` 的 `PHRASES` 清單
2. 執行生成：`uv run python generate_voice.py`
3. 確認 OK 後刪除已處理的 log 檔

### 2d. 刪除已處理 log
```bash
# 確認生成成功後才刪除
rm voice_missing_log/YYYY-MM-DD.txt
```

### 2e. Commit & Push
```bash
git add voice/map.zh-CN.json voice/ generate_voice.py voice_missing_log/
git commit -m "feat: 預錄缺失語音（來自部署機 log YYYY-MM-DD）"
git push
```

---

## 規則

- **每次對話開始時**：執行步驟 1，確認交接資料有無更新，有則立即告知使用者
- **每次對話開始時**：執行步驟 2a，若有新的 log 檔，執行 2b-2e
- log 只有在對應 WAV 全部成功生成後才能刪除
