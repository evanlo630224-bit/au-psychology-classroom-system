# AU-PCRS V5.0.4 Booking Review Hotfix

## 修正內容

修正管理員審核借用時發生的 `sqlalchemy.exc.IntegrityError`。

### 研判原因
早期 AU-PCRS 版本可能曾在 `bookings.status` 建立舊的 CHECK constraint，
只允許「有效」與「已取消」等狀態。後續版本新增：

- 待審核
- 已核准
- 已退回
- 已完成

`metadata.create_all()` 不會自動替換既有 constraint，因此審核更新為
「已核准」等新狀態時可能違反舊 constraint。

### 本版處理
- 啟動時自動檢查 `bookings` 的 CHECK constraints。
- 僅移除 SQL 表達式中包含 `status` 的舊 CHECK constraint。
- 將新借用預設狀態設為「待審核」。
- 審核狀態加入白名單驗證。
- 自動補齊 reviewer、review_note、reviewed_at、updated_at。
- 找不到借用紀錄時顯示友善提示。
- 審核錯誤不再直接讓整個管理後台崩潰。
- 保留 V5.0.3 的 Duplicate Key 與登出按鈕修正。

## 部署
將 ZIP 內容覆蓋 GitHub Repository 根目錄並 Commit。
Streamlit Cloud 重新啟動時會自動執行資料庫 migration。
不需要手動修改 Supabase。
