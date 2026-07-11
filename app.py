import io
import hashlib
import hmac
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


def configure_runtime_secrets():
    """Load Streamlit secrets into environment variables before DB import."""
    try:
        if "database" in st.secrets and "url" in st.secrets["database"]:
            os.environ.setdefault("DATABASE_URL", st.secrets["database"]["url"])
        if "admin" in st.secrets and "password" in st.secrets["admin"]:
            os.environ.setdefault("AU_PCRS_ADMIN_PASSWORD", st.secrets["admin"]["password"])
    except Exception:
        pass


configure_runtime_secrets()

from database import (
    add_course_blocks,
    cancel_booking,
    check_booking_conflict,
    create_booking,
    get_active_open_period,
    get_all_authorized_users,
    get_all_bookings,
    get_booking_by_id,
    get_course_blocks,
    get_course_semesters,
    get_dashboard_counts,
    get_audit_logs,
    get_database_backend,
    database_health_check,
    import_authorized_users,
    init_db,
    save_open_period,
    set_course_semester_active,
    delete_course_semester,
    update_booking,
    verify_authorized_user_by_code,
)

ROOMS = ["M502", "M506", "M507", "M510", "800A"]
TIME_SLOTS = [
    ("08:10", "09:00"), ("09:10", "10:00"), ("10:10", "11:00"),
    ("11:10", "12:00"), ("12:10", "13:00"), ("13:10", "14:00"),
    ("14:10", "15:00"), ("15:10", "16:00"), ("16:10", "17:00"),
    ("17:10", "18:00"), ("18:25", "19:10"), ("19:10", "19:55"),
    ("20:00", "20:45"), ("20:50", "21:35"), ("21:35", "22:20"),
]

ADMIN_PASSWORD = os.getenv("AU_PCRS_ADMIN_PASSWORD", "admin123")
ADMIN_SESSION_MINUTES = 30
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 5


def secure_compare(value, expected):
    return hmac.compare_digest(
        hashlib.sha256(value.encode("utf-8")).digest(),
        hashlib.sha256(expected.encode("utf-8")).digest(),
    )


def admin_session_expired():
    last = st.session_state.get("admin_last_activity")
    return not last or datetime.now() - last > timedelta(minutes=ADMIN_SESSION_MINUTES)


def touch_admin_session():
    st.session_state.admin_last_activity = datetime.now()

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "assets" / "psychology_logo.jpg"


def valid_email(email):
    return re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email.strip()) is not None


def valid_phone(phone):
    return len(re.sub(r"\D", "", phone)) >= 8


def excel_bytes(rows):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="借用紀錄")
    return output.getvalue()


def apply_style():
    st.markdown("""
    <style>
    :root {--purple:#4B20FF;--dark:#3010C8;--light:#F4F1FF;}
    .stApp{background:radial-gradient(circle at top right,rgba(75,32,255,.05),transparent 30%),#fff;}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#F4F1FF 0%,#FBFAFF 100%);border-right:1px solid #E0DAFF;}
    .title1{font-size:clamp(2rem,4vw,3.5rem);font-weight:850;color:#34219A;line-height:1.1;margin-bottom:8px;}
    .title2{font-size:clamp(1.7rem,3vw,2.8rem);font-weight:800;color:#252535;line-height:1.15;}
    .subtitle{margin-top:12px;color:#666078;font-size:1.1rem;}
    .version{display:inline-block;margin-top:12px;padding:5px 12px;border-radius:999px;background:#EDE8FF;color:#3010C8;font-size:.86rem;font-weight:700;}
    div[data-testid="stMetric"]{border:1px solid #E4DEFF;border-radius:18px;padding:16px;background:linear-gradient(180deg,#FFF,#FAF8FF);box-shadow:0 8px 24px rgba(75,32,255,.06);}
    .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700;}
    </style>
    """, unsafe_allow_html=True)


def header():
    left, right = st.columns([1, 4], vertical_alignment="center")
    with left:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=150)
    with right:
        st.markdown("""
        <div class="title1">亞洲大學心理學系</div>
        <div class="title2">專業教室借用及查詢系統</div>
        <div class="subtitle">AU Psychology Classroom Reservation System</div>
        <div class="version">AU-PCRS · Version 1.5 Cloud Beta</div>
        """, unsafe_allow_html=True)


st.set_page_config(page_title="AU-PCRS", layout="wide")
init_db()
apply_style()
for key, default in {"verified_user": None, "admin_logged_in": False, "admin_last_activity": None, "admin_failed_attempts": 0, "admin_locked_until": None, "privacy_agreed": False}.items():
    if key not in st.session_state:
        st.session_state[key] = default

language = st.sidebar.selectbox("語言 Language", ["中文", "English"])
page = st.sidebar.radio("功能 Menu", ["首頁", "我要借教室", "教室查詢", "管理員後台"])
header()

if st.session_state.admin_logged_in and admin_session_expired():
    st.session_state.admin_logged_in = False
    st.session_state.admin_last_activity = None
    st.warning("管理員登入已逾時，請重新登入。")

if page == "首頁":
    counts = get_dashboard_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("教師 / Faculty", counts["teachers"])
    c2.metric("學生 / Students", counts["students"])
    c3.metric("有效借用 / Active Bookings", counts["active_bookings"])
    c4.metric("教室 / Rooms", len(ROOMS))
    period = get_active_open_period()
    if period:
        st.success(f'目前開放借用期間：{period["start_date"]} ～ {period["end_date"]}')
    else:
        st.warning("目前尚未設定開放借用期間。")
    st.subheader("系統流程 / Workflow")
    st.write("匯入名冊 → 設定開放期間 → 匯入課表 → 身分驗證 → 借用教室")
    backend = get_database_backend()
    if backend == "PostgreSQL":
        st.success("雲端資料庫已連線：PostgreSQL")
    else:
        st.info("目前使用本機 SQLite。封閉雲端測試時，建議設定 PostgreSQL DATABASE_URL。")

elif page == "我要借教室":
    if st.session_state.verified_user is None:
        st.subheader("第一步：身分驗證")
        st.info("本系統會蒐集職編／學號、姓名、聯絡方式及借用事由，僅供心理學系教室管理使用。")
        st.session_state.privacy_agreed = st.checkbox(
            "我已閱讀並同意上述個人資料使用說明",
            value=st.session_state.privacy_agreed,
        )
        with st.form("verify_form"):
            identity = st.radio("身分類別", ["教師", "學生"])
            code = st.text_input("教師職編／學生學號")
            submit_verify = st.form_submit_button("驗證身分", use_container_width=True)
        if submit_verify:
            if not st.session_state.privacy_agreed:
                st.error("請先勾選同意個人資料使用說明。")
                st.stop()
            user = verify_authorized_user_by_code(identity, code)
            if user:
                st.session_state.verified_user = user
                st.rerun()
            else:
                st.error("身分驗證失敗。僅限心理學系教師及學生使用。")
    else:
        user = st.session_state.verified_user
        st.success(f'身分驗證成功：{user["user_type"]}｜{user["name"]}｜{user["identification_code"]}')
        if st.button("重新驗證／登出"):
            st.session_state.verified_user = None
            st.rerun()
        st.subheader("第二步：填寫借用資料")
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            with c1:
                booking_date = st.date_input("借用日期", value=date.today(), min_value=date.today())
                room = st.selectbox("教室", ROOMS)
                start_time = st.selectbox("開始時間", [s for s, _ in TIME_SLOTS])
                end_time = st.selectbox("結束時間", [e for _, e in TIME_SLOTS])
            with c2:
                phone = st.text_input("聯絡手機", placeholder="0912-345-678")
                email = st.text_input("聯絡信箱", value=user.get("email") or "")
                reason = st.text_area("借用事由")
            submitted = st.form_submit_button("送出申請", use_container_width=True)
        if submitted:
            if not phone.strip() or not email.strip() or not reason.strip():
                st.error("請完整填寫必填欄位。")
            elif not valid_phone(phone):
                st.error("手機格式不正確。")
            elif not valid_email(email):
                st.error("Email 格式不正確。")
            elif start_time >= end_time:
                st.error("結束時間必須晚於開始時間。")
            else:
                period = get_active_open_period()
                if not period or not (period["start_date"] <= str(booking_date) <= period["end_date"]):
                    st.error("所選日期不在開放借用期間內。")
                else:
                    conflict = check_booking_conflict(str(booking_date), room, start_time, end_time)
                    if conflict:
                        st.error("該時段已有課程或借用紀錄，無法借用。")
                        st.caption(conflict["detail"])
                    else:
                        booking_id = create_booking(
                            str(booking_date), room, start_time, end_time,
                            user["user_type"], user["name"], user["identification_code"],
                            phone.strip(), email.strip(), reason.strip()
                        )
                        st.success("借用申請已成功送出")
                        st.info(f"借用編號：{booking_id}")

elif page == "教室查詢":
    st.subheader("教室查詢")
    c1, c2 = st.columns(2)
    with c1:
        q_date = st.date_input("日期", value=date.today())
    with c2:
        q_room = st.selectbox("教室", ROOMS)
    courses = get_course_blocks(str(q_date), q_room)
    bookings = [r for r in get_all_bookings() if r["booking_date"] == str(q_date) and r["room"] == q_room and r["status"] == "有效"]
    rows = []
    for start, end in TIME_SLOTS:
        status, detail = "可借用", ""
        for course in courses:
            if start < course["end_time"] and end > course["start_time"]:
                status, detail = "已排課", course["course_name"]
                break
        if status == "可借用":
            for booking in bookings:
                if start < booking["end_time"] and end > booking["start_time"]:
                    status, detail = "已借用", ""
                    break
        rows.append({"時間": f"{start}～{end}", "狀態": status, "說明": detail})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

else:
    if not st.session_state.admin_logged_in:
        locked_until = st.session_state.get("admin_locked_until")
        now = datetime.now()
        if locked_until and now < locked_until:
            remaining = int((locked_until - now).total_seconds())
            st.error(f"登入暫時鎖定，請於 {remaining} 秒後再試。")
        else:
            if locked_until and now >= locked_until:
                st.session_state.admin_locked_until = None
                st.session_state.admin_failed_attempts = 0
            with st.form("admin_login"):
                password = st.text_input("管理員密碼", type="password")
                login = st.form_submit_button("登入")
            if login:
                if secure_compare(password, ADMIN_PASSWORD):
                    st.session_state.admin_logged_in = True
                    st.session_state.admin_failed_attempts = 0
                    st.session_state.admin_locked_until = None
                    touch_admin_session()
                    st.rerun()
                else:
                    st.session_state.admin_failed_attempts += 1
                    remaining_attempts = MAX_LOGIN_ATTEMPTS - st.session_state.admin_failed_attempts
                    if st.session_state.admin_failed_attempts >= MAX_LOGIN_ATTEMPTS:
                        st.session_state.admin_locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                        st.error("登入失敗次數過多，暫時鎖定 5 分鐘。")
                    else:
                        st.error(f"管理員密碼錯誤，尚可嘗試 {remaining_attempts} 次。")
    else:
        touch_admin_session()
        _, logout_col = st.columns([5, 1])
        with logout_col:
            if st.button("管理員登出"):
                st.session_state.admin_logged_in = False
                st.session_state.admin_last_activity = None
                st.rerun()
        tabs = st.tabs(["Dashboard", "名冊管理", "開放借用期間", "課表管理", "借用紀錄管理", "操作紀錄", "資料備份", "部署狀態"])
        with tabs[0]:
            counts = get_dashboard_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric("教師", counts["teachers"])
            c2.metric("學生", counts["students"])
            c3.metric("有效借用", counts["active_bookings"])
        with tabs[1]:
            user_type = st.radio("名冊類型", ["教師", "學生"], horizontal=True)
            uploaded = st.file_uploader("上傳 Excel（辨識碼、姓名、聯絡信箱、狀態）", type=["xlsx"], key=f"roster_{user_type}")
            replace = st.checkbox("覆蓋此類名冊")
            if st.button("開始匯入", key="import_roster"):
                if uploaded is None:
                    st.error("請先選擇 Excel 檔案。")
                else:
                    result = import_authorized_users(pd.read_excel(uploaded, dtype=str).fillna(""), user_type, replace)
                    st.success(f'新增 {result["inserted"]}、更新 {result["updated"]}、略過 {result["skipped"]}')
            roster = get_all_authorized_users()
            if roster:
                st.dataframe(pd.DataFrame(roster), use_container_width=True, hide_index=True)
        with tabs[2]:
            c1, c2 = st.columns(2)
            with c1:
                p_start = st.date_input("開始日期", value=date.today(), key="p_start")
            with c2:
                p_end = st.date_input("結束日期", value=date.today(), key="p_end")
            semester = st.text_input("學期", value="115-1")
            if st.button("儲存並啟用"):
                if p_start > p_end:
                    st.error("開始日期不可晚於結束日期。")
                else:
                    save_open_period(semester, str(p_start), str(p_end))
                    st.success("開放借用期間已儲存。")
        with tabs[3]:
            st.subheader("學期課表管理")
            st.caption("Excel 欄位：教室、星期、開始時間、結束時間、課程名稱、教師")

            semester_name = st.text_input("匯入學期", value="115-1", key="course_semester")
            schedule = st.file_uploader("上傳課表 Excel", type=["xlsx"], key="schedule")
            replace_semester = st.checkbox("匯入前先清除該學期既有課表", key="replace_semester")

            preview_df = None
            if schedule is not None:
                try:
                    preview_df = pd.read_excel(schedule, dtype=str).fillna("")
                    st.markdown("**匯入預覽（前 20 筆）**")
                    st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
                    st.caption(f"檔案共 {len(preview_df)} 筆資料。")
                except Exception as exc:
                    st.error(f"無法讀取 Excel：{exc}")

            if st.button("確認匯入課表", key="import_schedule"):
                if schedule is None or preview_df is None:
                    st.error("請先選擇並確認課表 Excel。")
                elif not semester_name.strip():
                    st.error("請輸入學期，例如 115-1。")
                else:
                    try:
                        result = add_course_blocks(
                            preview_df,
                            semester=semester_name.strip(),
                            replace=replace_semester,
                        )
                        st.success(
                            f'匯入完成：新增 {result["inserted"]}、'
                            f'重複略過 {result["duplicates"]}、格式略過 {result["skipped"]}。'
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"課表匯入失敗：{exc}")

            st.divider()
            st.markdown("**目前學期課表**")
            semester_rows = get_course_semesters()
            if semester_rows:
                st.dataframe(pd.DataFrame(semester_rows), use_container_width=True, hide_index=True)
                semester_options = [row["semester"] for row in semester_rows]
                manage_semester = st.selectbox("選擇管理學期", semester_options, key="manage_semester")
                current_row = next(row for row in semester_rows if row["semester"] == manage_semester)
                active_value = bool(current_row["is_active"])
                desired_active = st.checkbox("啟用此學期課表", value=active_value, key=f"active_{manage_semester}")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("儲存啟用狀態", key="save_semester_active"):
                        set_course_semester_active(manage_semester, desired_active)
                        st.success("學期課表狀態已更新。")
                        st.rerun()
                with col_b:
                    confirm_delete = st.checkbox("我確認要刪除此學期全部課表", key="confirm_delete_semester")
                    if st.button("刪除此學期課表", key="delete_semester"):
                        if not confirm_delete:
                            st.error("請先勾選刪除確認。")
                        else:
                            deleted = delete_course_semester(manage_semester)
                            st.success(f"已刪除 {manage_semester} 共 {deleted} 筆課表資料。")
                            st.rerun()
            else:
                st.info("目前尚無課表資料。")
        with tabs[4]:
            st.subheader("借用紀錄管理")
            all_rows = get_all_bookings()
            if not all_rows:
                st.info("目前尚無借用紀錄。")
            else:
                f1, f2, f3 = st.columns(3)
                with f1:
                    filter_room = st.selectbox("教室篩選", ["全部"] + ROOMS)
                with f2:
                    filter_status = st.selectbox("狀態篩選", ["全部", "有效", "已取消"])
                with f3:
                    keyword = st.text_input("姓名／借用編號")
                d1, d2 = st.columns(2)
                with d1:
                    filter_start = st.date_input("起始日期", value=date.today(), key="filter_start")
                with d2:
                    filter_end = st.date_input("結束日期", value=date.today(), key="filter_end")
                filtered = []
                for row in all_rows:
                    if filter_room != "全部" and row["room"] != filter_room:
                        continue
                    if filter_status != "全部" and row["status"] != filter_status:
                        continue
                    if keyword.strip() and keyword.strip().lower() not in f'{row["booking_id"]} {row["applicant_name"]}'.lower():
                        continue
                    if not (str(filter_start) <= row["booking_date"] <= str(filter_end)):
                        continue
                    filtered.append(row)
                if filtered:
                    st.dataframe(pd.DataFrame(filtered), use_container_width=True, hide_index=True)
                    st.download_button("匯出目前篩選結果 Excel", data=excel_bytes(filtered), file_name=f"借用紀錄_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("查無符合條件的紀錄。")
                st.divider()
                st.subheader("修改或取消借用")
                ids = [r["booking_id"] for r in all_rows]
                selected_id = st.selectbox("選擇借用編號", ids)
                selected = get_booking_by_id(selected_id)
                if selected:
                    c1, c2 = st.columns(2)
                    with c1:
                        edit_date = st.date_input("借用日期", value=date.fromisoformat(selected["booking_date"]), key=f"edit_date_{selected_id}")
                        edit_room = st.selectbox("教室", ROOMS, index=ROOMS.index(selected["room"]), key=f"edit_room_{selected_id}")
                    with c2:
                        starts = [s for s, _ in TIME_SLOTS]
                        ends = [e for _, e in TIME_SLOTS]
                        edit_start = st.selectbox("開始時間", starts, index=starts.index(selected["start_time"]), key=f"edit_start_{selected_id}")
                        edit_end = st.selectbox("結束時間", ends, index=ends.index(selected["end_time"]), key=f"edit_end_{selected_id}")
                    edit_reason = st.text_area("借用事由", value=selected["reason"], key=f"edit_reason_{selected_id}")
                    if st.button("儲存修改", key=f"save_{selected_id}"):
                        if selected["status"] != "有效":
                            st.error("已取消的紀錄不可修改。")
                        elif edit_start >= edit_end:
                            st.error("結束時間必須晚於開始時間。")
                        else:
                            conflict = check_booking_conflict(str(edit_date), edit_room, edit_start, edit_end, exclude_booking_id=selected_id)
                            if conflict:
                                st.error("修改後的時段與課程或其他借用衝突。")
                                st.caption(conflict["detail"])
                            else:
                                update_booking(selected_id, str(edit_date), edit_room, edit_start, edit_end, edit_reason.strip())
                                st.success("借用紀錄已更新。")
                                st.rerun()
                    cancel_reason = st.text_input("取消原因", key=f"cancel_reason_{selected_id}")
                    if st.button("取消此借用", key=f"cancel_{selected_id}"):
                        if selected["status"] != "有效":
                            st.error("此筆紀錄已取消。")
                        elif not cancel_reason.strip():
                            st.error("請填寫取消原因。")
                        else:
                            cancel_booking(selected_id, cancel_reason.strip())
                            st.success("借用已取消，歷史紀錄仍會保留。")
                            st.rerun()

        with tabs[5]:
            st.subheader("操作紀錄")
            logs = get_audit_logs(1000)
            if logs:
                st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
                st.download_button(
                    "匯出操作紀錄 Excel",
                    data=excel_bytes(logs),
                    file_name=f"操作紀錄_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("目前尚無操作紀錄。")

        with tabs[6]:
            st.subheader("資料庫備份")
            st.warning("備份檔包含名冊、聯絡方式與借用紀錄，請妥善保管。")
            if get_database_backend() == "SQLite":
                db_file = BASE_DIR / "classroom_booking.db"
                if db_file.exists():
                    st.download_button(
                        "下載 SQLite 備份檔",
                        data=db_file.read_bytes(),
                        file_name=f"classroom_booking_backup_{date.today()}.db",
                        mime="application/octet-stream",
                    )
                else:
                    st.info("目前找不到資料庫檔案。")
            else:
                st.info("目前使用 PostgreSQL。請同時啟用資料庫供應商的自動備份功能。")
                backup_rows = get_all_bookings()
                if backup_rows:
                    st.download_button(
                        "匯出全部借用紀錄 Excel",
                        data=excel_bytes(backup_rows),
                        file_name=f"全部借用紀錄_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

        with tabs[7]:
            st.subheader("部署狀態 / Deployment Status")
            ok, message = database_health_check()
            c1, c2 = st.columns(2)
            c1.metric("資料庫後端", get_database_backend())
            c2.metric("資料庫連線", "正常" if ok else "異常")
            if ok:
                st.success(message)
            else:
                st.error(message)
            if ADMIN_PASSWORD == "admin123":
                st.error("仍在使用預設管理員密碼 admin123，正式測試前必須更換。")
            else:
                st.success("管理員密碼已由環境變數或 Streamlit Secrets 提供。")
            st.code(
                '[database]\nurl = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME"\n\n'
                '[admin]\npassword = "請設定高強度密碼"',
                language="toml",
            )
