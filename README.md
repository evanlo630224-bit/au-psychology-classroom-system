# AU-PCRS V8.1 Refined Login Edition

## 本版本修正
- 登入前不再顯示大面積紫色側欄。
- 語言切換移至頂部右側，修正選單文字空白問題。
- 登入標題、身分選擇、帳號欄位與按鈕整合為同一張卡片。
- 隱藏 Streamlit Share、GitHub、編輯及工具列控制項。
- Logo 改為縮小整合呈現，並以混合模式降低白色底框突兀感。
- 功能卡片全面改用一致的 SVG 線性圖示。
- 縮減 Hero、卡片及頁尾高度，提升一般桌面解析度的完整呈現率。
- 保留 V8.0 既有的登入、名冊、課表、衝堂、借用、查詢、後台與稽核功能。

## Logo
請將正式 Logo 放入：
- `assets/psychology_logo.jpg`
- `assets/asia_university_logo.png`

如能提供透明背景 PNG，首頁效果會更佳；也可將 `PSY_LOGO` 的檔名改成透明 PNG。

## 本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署
將本資料夾內容上傳至原 GitHub Repository，保留 Streamlit Cloud 原有 Supabase Secrets，重新部署即可。
