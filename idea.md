## 日/夜模式切換功能（2026-03-30）

### 重點決策
- 使用 Tailwind `darkMode: 'class'` 策略
- 預設跟隨系統 `prefers-color-scheme`
- 使用者手動切換後存入 localStorage，不再跟隨系統
- 亮色模式使用暖色品牌色（橘/金色 warm 色板），暗色模式維持原有品牌藍
- 切換按鈕在 Navbar 右側（太陽/月亮圖示）
- FOUC 防護：main.jsx 渲染前立即初始化 `<html>` class

### 涉及檔案
- ThemeContext.jsx（新增）
- main.jsx、App.jsx、tailwind.config.js、index.css（基礎建設）
- Navbar、Footer、FloatingCart（元件）
- Home、Product、Purchase、PurchaseResult、Team、Download、Project、Announcements（頁面）

---

## 3D 模型攝影機高度 + 日間模式模糊圓圈（2026-03-31）

### 需求
1. 日間模式下白色 3D 模型在灰色背景上不夠突出 → 加入模糊圓圈背景裝飾
2. 不同商品的 3D 模型大小不同，攝影機高度需要個別調整 → 後台新增 camera_height 欄位

### 重點決策
- 後端 Product model 新增 `camera_height` FloatField（預設 0.5）
- 前端 ModelViewer 接收 `cameraHeight` prop 動態調整攝影機 Y 軸位置
- 日間模式模糊圓圈使用 `bg-gray-200/20`（Home）/ `bg-gray-200/30`（Product），暗色模式 `dark:bg-transparent` 隱藏
- 後台管理面板新增攝影機高度編輯欄位，管理員可依商品大小調整（預設 0.5，較大模型可設 1.0~2.0）
- Migration 需在 Docker 容器內執行（entrypoint.sh 會自動 makemigrations + migrate）

### 涉及檔案
- models.py、serializers.py、admin.py、admin_views.py（後端）
- ModelViewer.jsx（cameraHeight prop）
- Home.jsx、Product.jsx（模糊圓圈 + cameraHeight）
- admin/sections/Products.jsx（後台編輯欄位）
