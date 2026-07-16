# AU-PCRS V5.0.3 Stable Hotfix

## 修正內容

修正管理員後台出現：

```text
StreamlitDuplicateElementKey
```

### 原因
`analytics_dashboard()` 同時出現在管理員 Dashboard 與 Analytics 分頁，
兩個 `st.selectbox` 都使用相同的 `key="analytics_days"`。

`weekly_schedule_view()` 也可能同時出現在不同頁面，原本共用：
- `week_start`
- `week_room`

### 修正方式
所有可重複顯示的元件都加入頁面前綴：

- 首頁統計：`home_analytics_days`
- 管理員統計：`admin_analytics_analytics_days`
- 管理員週課表：`admin_analytics_week_start`
- 使用者週課表：`user_weekly_week_start`
- 各頁教室選單也使用獨立 key

本版同時保留 V5.0.2 的側邊欄登出按鈕顯示修正。

## 部署
將 ZIP 內容覆蓋 GitHub Repository 根目錄並 Commit，
等待 Streamlit Cloud 自動重新部署。
