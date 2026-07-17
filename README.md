# AU-PCRS V7.0.3 Import Compatibility Hotfix

## 修正內容

修正 Streamlit Cloud 啟動時發生的 ImportError。

### 原因
在 GitHub 多檔案更新或 Streamlit Cloud rolling deployment 過程中，
`app.py` 可能先更新，但 `database.py` 尚未切換到同一版本。
此時 app.py 直接匯入新版函式會出現 ImportError。

### 本版處理
- 移除對 `update_announcement_bilingual` 的強制直接匯入。
- 改由 app.py 使用相容性資料庫存取層。
- 啟動及儲存公告時自動確認 `title_en`、`content_en` 欄位。
- 即使 database.py 短暫仍是舊版，系統也能正常啟動。
- 保留中文公告自動翻譯成英文的功能。

## 部署
請將 ZIP 內所有檔案一次完整覆蓋 GitHub Repository 根目錄。
尤其必須同步更新：
- app.py
- database.py
- translation.py
- requirements.txt
