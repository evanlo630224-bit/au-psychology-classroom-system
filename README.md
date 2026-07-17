# AU-PCRS V6.0 Enterprise AI

## AI 智慧功能

- AI 智慧營運摘要
- 核准率與待審核比例分析
- 熱門教室與尖峰日期分析
- 每月借用量增減趨勢
- 教室即時可用狀況摘要
- 跨模組智慧搜尋
  - 借用編號
  - 姓名
  - 職編／學號
  - 教室
  - 用途
  - 狀態
  - 公告
- AI 空間推薦
  - 自動排除停借
  - 自動排除課程
  - 自動排除既有借用
- 管理員 AI Center
- 教師與學生 AI 智慧助理

## 說明

本版 AI 採用可驗證的規則式分析與資料庫智慧查詢，
不會將校內名冊或借用資料傳送至外部 AI 服務，
因此不需新增 API Key，也不需修改 Streamlit Secrets。

## 部署

將 ZIP 內全部檔案覆蓋 GitHub Repository 根目錄並 Commit。
Streamlit Cloud 會自動重新部署。
