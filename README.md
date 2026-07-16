# AU-PCRS V4.1.1 Enterprise Stable Hotfix

## 修正內容

修正 PostgreSQL 在課表學期彙整時發生的錯誤：

```text
function max(boolean) does not exist
```

V4.1 原本對 `course_blocks.is_active` 使用 `MAX()`。
PostgreSQL 不支援對 Boolean 欄位執行 `MAX()`，本版改為：

- PostgreSQL：`BOOL_OR(is_active)`
- SQLite：`MAX(is_active)`

此修正不需要更改 Streamlit Secrets，也不需要手動修改 Supabase 資料表。
