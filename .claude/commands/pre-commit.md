---
allowed-tools: Read, Bash(git:*), Bash(cp:*), Bash(grep:*), Bash(ls:*)
description: Push 前安全確認 + 交接資料同步
---

## Push 前必做流程（依序執行）

### Step 1：同步機密檔到 `_交接資料/`

```bash
cp .env _交接資料/.env
```

若 `Website/.env` 有異動：
```bash
cp Website/.env _交接資料/Website.env
```

若 `google_Speech_to_Text.json` 或 `Google_Api_Key.json` 有異動：
```bash
cp google_Speech_to_Text.json _交接資料/
cp Google_Api_Key.json _交接資料/
```

> `_交接資料/` 在 `.gitignore`，不會進 git。同步是為了讓另一台電腦 pull 後能從這裡還原機密檔。

---

### Step 2：確認沒有機密檔被 staged

```bash
git diff --cached --name-only
```

以下**絕對不能出現**在 staged 清單：
- `.env`
- `*.json`（服務帳號金鑰）
- `*.pt`、`*.task`（模型檔）
- `_交接資料/`
- `Website/downloads/`、`*.apk`、`mobileclip*.ts`

---

### Step 3：確認沒有 merge conflict 殘留

```bash
grep -rn "<<<<<<\|=======\|>>>>>>" --include="*.py" --include="*.md" . | grep -v ".venv"
```

---

### Step 4：確認 `.claude/commands/` 已包含在 staged 內

SKILL 檔要隨 push 同步到其他電腦：

```bash
git status .claude/commands/
```

若有修改未 staged，執行：
```bash
git add .claude/commands/
```

---

全部確認無誤後執行 commit & push。
