# AU-PCRS V5.0.2 Sidebar Logout Button Hotfix

## 修正內容

修正左側選單「登出」按鈕文字平時不可見、需將游標移入才顯示的問題。

### 修正方式
- 明確設定側邊欄按鈕背景為白色。
- 按鈕文字固定為深紫色。
- Hover、Focus、Active 狀態維持清楚對比。
- 強制文字與子元素 opacity 為 1。
- 保留既有按鈕圓角及整體紫色介面。

## 部署
將 ZIP 內容覆蓋 GitHub Repository 根目錄並 Commit，
等待 Streamlit Cloud 自動重新部署。
