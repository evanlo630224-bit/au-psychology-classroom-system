# AU-PCRS V4.0 Enterprise

## 主要功能
- 教師、學生、管理員登入
- Excel 名冊匯入／匯出
- 教室管理：容量、位置、設備、啟用／停用
- 開放借用期間
- 課表匯入與衝突檢查
- 停借日期與特定教室停借
- 人工審核或自動核准模式
- 借用審核：核准、退回、取消、完成
- 公告管理
- 教室行事曆
- 個人借用紀錄
- QR Code 與 PDF 借用證明
- Excel 報表
- 操作紀錄
- 選配 SMTP Email 通知
- Supabase PostgreSQL + Streamlit Cloud

## Streamlit Secrets

```toml
[database]
host = "aws-0-ap-northeast-1.pooler.supabase.com"
port = 5432
name = "postgres"
user = "postgres.PROJECT_REF"
password = "DATABASE_PASSWORD"

ADMIN_PASSWORD = "ADMIN_PASSWORD"

# Optional email notifications
[smtp]
host = "smtp.gmail.com"
port = 465
username = "your_account@gmail.com"
password = "APP_PASSWORD"
from_email = "your_account@gmail.com"
```

## 部署
將本專案內容覆蓋到 GitHub Repository 根目錄，Commit 後等待 Streamlit Cloud 自動重新部署。
首次啟動會自動建立 V4.0 新資料表並補上 bookings 新欄位。
