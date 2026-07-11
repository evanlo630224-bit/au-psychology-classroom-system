# AU-PCRS V1.5 Cloud Beta 部署說明

## 建議架構
- Streamlit Community Cloud：執行網站
- PostgreSQL（Supabase、Neon 或校方資料庫）：永久保存資料
- GitHub 私人儲存庫：保存程式碼，不放任何名冊或資料庫檔

## Streamlit Secrets
在雲端 App 的 Secrets 貼入：

```toml
[database]
url = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME"

[admin]
password = "高強度管理員密碼"
```

## 部署步驟
1. 建立私人 GitHub 儲存庫並上傳本專案。
2. 不要上傳 `classroom_booking.db` 或 `.streamlit/secrets.toml`。
3. 建立 PostgreSQL 資料庫並複製連線字串。
4. 在 Streamlit Community Cloud 建立 App，Main file path 設為 `app.py`。
5. 在 Advanced settings → Secrets 貼入上方設定。
6. 部署後，以少量測試名冊做封閉 Beta。
7. 確認新增、修改、取消、課表衝突、重新啟動後資料仍存在。

## 正式開放前
- 改用校內 SSO 或 Email 驗證碼。
- 完成個資告知與使用規範。
- 確認資料庫自動備份。
- 限制管理員名單與權限。
