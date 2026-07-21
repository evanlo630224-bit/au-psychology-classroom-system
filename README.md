# AU-PCRS V8.0 Professional UI Edition

## 本版本重點
- 依新版首頁 UI 模擬圖重做登入畫面
- 雙欄式品牌主視覺與專業登入卡片
- 中文／English 雙語切換
- 教師、學生、管理員三種身分登入
- 保留名冊匯入、開放期間、課表匯入、衝堂檢查
- 保留教室借用、教室查詢、借用修改／取消、稽核紀錄
- 支援 Supabase PostgreSQL，未設定時自動使用 SQLite
- 教室：M502、M506、M507、M510、800A

## Logo 檔名
- `assets/psychology_logo.jpg`
- `assets/asia_university_logo.png`

Logo 未放入時，系統仍可啟動，只是不顯示圖片。

## 本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 更新
1. 將整個資料夾內容上傳至 GitHub repository。
2. 保留原本 Streamlit Cloud 的 Supabase Secrets。
3. Main file path 設為 `app.py`。
4. Deploy／Reboot app。

升級前請先備份 Supabase。
