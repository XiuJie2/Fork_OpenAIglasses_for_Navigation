---
allowed-tools: Read, Edit, Write
description: 更新 MD/idea.md 與 memory/MEMORY.md
---

每次對話結束前，或產生新決策時執行。

## 必須更新的文件

| 文件 | 路徑 | 更新時機 |
|------|------|---------|
| idea.md | `MD/idea.md` | 每次對話，記錄新想法、待實作、已實作 |
| MEMORY.md | `memory/MEMORY.md` | 有新的偏好或專案決策時 |

## 執行規則

- 不允許只口頭說「記得更新」，必須實際寫入
- idea.md 新內容加在對應分類下，標記日期
- MEMORY.md 如有新 memory 檔案，同步更新索引

## idea.md 寫入格式

```markdown
## 功能名稱（狀態，日期）

### 決策重點
- 決定了什麼、為什麼

### 涉及檔案
- `檔案名.py`：改了什麼
```
