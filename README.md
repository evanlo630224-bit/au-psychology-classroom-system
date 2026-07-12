# AU-PCRS V2.0 Cloud

本版已修正：

- Streamlit Secrets 直接讀取 `DATABASE_URL`，也相容 `[database].url`
- PostgreSQL / Supabase 與 SQLite 自動切換
- PostgreSQL 正確欄位型別：DATE、TIME、BOOLEAN、TIMESTAMPTZ
- 中英文登入首頁
- 教師、學生、管理員三種登入
- 教室借用、查詢、名冊、課表、開放期間、借用管理、操作紀錄

## Streamlit Secrets

```toml
DATABASE_URL = "postgresql+psycopg://postgres.PROJECT_REF:DATABASE_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require"
ADMIN_PASSWORD = "您的新管理員密碼"
```

請勿將真實 Secrets 上傳 GitHub。
