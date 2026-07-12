
# AU-PCRS V2.1 Repair

亞洲大學心理學系專業教室借用及查詢系統

## V2.1 修正內容

- Supabase Session Pooler 改用拆分式 Secrets
- 強制使用 `postgres.PROJECT_REF` 帳號
- 使用 SQLAlchemy `URL.create()`，避免密碼特殊字元造成 URI 解析錯誤
- 移除對 Streamlit Secrets 內舊 `DATABASE_URL` 的依賴
- PostgreSQL 連線加入 SSL 與逾時設定
- 本機未設定 Secrets 時自動改用 SQLite
- 中英文登入首頁
- 教師、學生、管理員登入
- 教室借用、查詢、名冊、課表、開放期間、借用管理與操作紀錄

## Streamlit Secrets

Streamlit Community Cloud → App settings → Secrets：

```toml
[database]
host = "aws-0-ap-northeast-1.pooler.supabase.com"
port = 5432
name = "postgres"
user = "postgres.YOUR_PROJECT_REF"
password = "YOUR_DATABASE_PASSWORD"

ADMIN_PASSWORD = "YOUR_NEW_ADMIN_PASSWORD"
```

Secrets 中請刪除所有舊的：

```toml
DATABASE_URL = "..."
```

或：

```toml
[database]
url = "..."
```

## 更新 GitHub

將 ZIP 內下列檔案覆蓋到 Repository 根目錄：

- `app.py`
- `database.py`
- `requirements.txt`
- `runtime.txt`
- `.streamlit/config.toml`
- `assets/psychology_logo.jpg`

Commit 後等待 Streamlit Cloud 自動重新部署，或手動 Reboot app。
