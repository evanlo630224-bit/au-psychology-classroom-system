# AU-PCRS V8.4 Sidebar Visibility Fix Edition

## 本版本修正
- 登入前不再顯示大面積紫色側欄。
- 語言切換移至頂部右側，修正選單文字空白問題。
- 登入標題、身分選擇、帳號欄位與按鈕整合為同一張卡片。
- 隱藏 Streamlit Share、GitHub、編輯及工具列控制項。
- Logo 改為縮小整合呈現，並以混合模式降低白色底框突兀感。
- 功能卡片全面改用一致的 SVG 線性圖示。
- 縮減 Hero、卡片及頁尾高度，提升一般桌面解析度的完整呈現率。
- 保留 V8.0 既有的登入、名冊、課表、衝堂、借用、查詢、後台與稽核功能。

## Logo
請將正式 Logo 放入：
- `assets/psychology_logo.jpg`
- `assets/asia_university_logo.png`

如能提供透明背景 PNG，首頁效果會更佳；也可將 `PSY_LOGO` 的檔名改成透明 PNG。

## 本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署
將本資料夾內容上傳至原 GitHub Repository，保留 Streamlit Cloud 原有 Supabase Secrets，重新部署即可。


## V8.2 修正內容
- 將 `home()` 改名為 `render_dashboard()`，避免與其他物件或頁面名稱混淆。
- 所有首頁與管理員儀表板均直接呼叫渲染函式，不再把 Streamlit `DeltaGenerator` 當成內容輸出。
- 明確禁止使用 `st.write(render_dashboard())`、`st.write(st.markdown(...))` 等寫法。
- 更新畫面版本標示為 V8.3 Streamlit Magic Fix Edition。


## V8.3 修正重點
- 修正 `st.info(...) if ok else st.error(...)` 被 Streamlit Magic 當成一般運算式輸出。
- 改為標準 `if/else` 區塊，不再回傳或顯示 `DeltaGenerator`。
- 所有頁面渲染函式皆以 `_ = render_function()` 明確呼叫，避免 Magic 自動顯示函式回傳值。
- 登入頁、首頁、借用頁、查詢頁與管理後台皆套用相同防護。


## V8.4 修正內容
- 修正登入後側欄語言選單白字白底問題
- 修正功能選單只顯示圓形按鈕、名稱消失問題
- 選中功能使用淡紫底與深紫字提示
- 未選功能使用白底深紫字
- 側欄 Logo 縮小並加上圓角與柔和陰影
- 登出按鈕改為白底深紫字
- 將版本資訊移至側欄底部並降低視覺干擾
- 保留 V8.3 的 Streamlit Magic / DeltaGenerator 修正
