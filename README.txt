AU-PCRS V1.2 Beta
=================

新增功能
--------
1. 管理員可依教室、狀態、日期、姓名及借用編號篩選。
2. 管理員可修改借用日期、教室、時段及事由。
3. 修改時重新檢查正式課表與其他借用衝突。
4. 管理員可取消借用並記錄原因。
5. 已取消資料保留，不直接刪除。
6. 可將目前篩選結果匯出 Excel。
7. 前台查詢不公開申請人姓名。
8. 新增 audit_logs 操作紀錄資料表。
9. 系統標題分兩列顯示，側邊欄不再重複顯示 Logo。

安裝方式
--------
1. 先備份原本的 classroom_booking.db。
2. 將本專案的 app.py、database.py、requirements.txt、assets、.streamlit
   複製到原專案資料夾。
3. 保留原本的 classroom_booking.db，可沿用舊資料。
4. 在命令提示字元執行：

   cd C:\Users\USER\Desktop\psychology_classroom_system
   venv\Scripts\activate
   python -m pip install -r requirements.txt
   python -m streamlit run app.py

管理員預設密碼：admin123
正式使用前請設定環境變數 AU_PCRS_ADMIN_PASSWORD。

建議測試
--------
1. 新增一筆借用。
2. 到管理員後台「借用紀錄管理」查看。
3. 修改日期、教室或時段。
4. 嘗試修改到衝突時段，確認系統阻擋。
5. 填寫取消原因後取消借用。
6. 匯出 Excel，確認狀態與取消原因存在。


V1.3 Security 更新
------------------
1. 管理員登入失敗 5 次後鎖定 5 分鐘。
2. 管理員閒置 30 分鐘後自動登出。
3. 新增管理員手動登出。
4. 新增操作紀錄檢視與 Excel 匯出。
5. 新增 SQLite 資料庫備份下載。
6. 正式上線前請以 AU_PCRS_ADMIN_PASSWORD 設定強密碼。


AU-PCRS V1.4 Semester 更新
--------------------------
1. 課表依學期管理，例如 115-1、115-2。
2. 匯入前顯示 Excel 前 20 筆預覽與資料筆數。
3. 同一學期、教室、星期、時段、課程與教師完全相同時，自動略過重複資料。
4. 可選擇匯入前清除該學期既有課表。
5. 可啟用或停用整個學期課表。
6. 可刪除指定學期的全部課表，並要求二次確認。
7. 借用衝突檢查會依目前開放借用期間所設定的學期套用課表。
8. 舊版課表會自動歸入「未分類」，不會直接遺失。


AU-PCRS V1.5 Cloud Beta 更新
----------------------------
1. 支援 PostgreSQL 雲端資料庫，未設定時自動使用本機 SQLite。
2. 支援 Streamlit Secrets 設定資料庫與管理員密碼。
3. 新增資料庫連線健康檢查與部署狀態頁籤。
4. 首頁顯示目前資料庫後端。
5. 身分驗證前加入個人資料使用同意。
6. PostgreSQL 模式下改提供 Excel 匯出，資料庫備份由供應商管理。
7. 新增 DEPLOYMENT.md、secrets 範本、.gitignore 與 runtime.txt。
