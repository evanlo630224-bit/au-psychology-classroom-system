# AU-PCRS V4.1 Enterprise Stable

## Stable 修正

- 修正 PostgreSQL `timestamptz` 匯出 Excel 時產生的 `ValueError`
- 所有 Excel 匯出自動將時區日期轉成可寫入格式
- 空名冊顯示提示，不再建立無效下載
- 開放期間、公告、停借資料加入輸入驗證
- Email 未設定或寄送失敗時不影響主要流程
- PDF 借用證明加入文字安全處理
- 公告與停借操作寫入 Audit Log
- 保留 V4.0 的名冊、教室、課表、審核、公告、停借、QR Code、PDF、Email 與報表功能

## Streamlit Secrets

```toml
[database]
host = "aws-0-ap-northeast-1.pooler.supabase.com"
port = 5432
name = "postgres"
user = "postgres.PROJECT_REF"
password = "DATABASE_PASSWORD"

ADMIN_PASSWORD = "ADMIN_PASSWORD"

# Optional
[smtp]
host = "smtp.gmail.com"
port = 465
username = "your_account@gmail.com"
password = "APP_PASSWORD"
from_email = "your_account@gmail.com"
```

## 部署

將 ZIP 內檔案覆蓋到 GitHub Repository 根目錄，Commit 後等待 Streamlit Cloud 自動重新部署。
