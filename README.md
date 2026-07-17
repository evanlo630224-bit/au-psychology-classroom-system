# AU-PCRS V7.0.4 AI Pro NameError Hotfix

## 修正內容

修正管理員後台開啟 AI Center 時出現：

```text
NameError: ai_pro_center is not defined
```

### 原因
V7.0.3 在合併公告相容性修正時，AI Pro 的下列函式沒有完整保留：

- ai_pro_center
- demand_forecast_panel
- approval_assistant_panel
- utilization_heatmap_panel
- ai_chat_panel
- tv_mode_page

### 本版處理
- 完整補回 AI Pro 功能。
- 保留中文公告自動翻譯。
- 保留雙語公告顯示。
- 保留 Import Compatibility 修正。
- TV 營運看板同步顯示中英文公告。

## 部署
請將 ZIP 內全部檔案一次覆蓋 GitHub Repository 根目錄。
