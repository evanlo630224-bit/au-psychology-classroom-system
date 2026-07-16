import io
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from database import (
    add_course_blocks,
    cancel_booking,
    check_booking_conflict,
    create_booking,
    database_health_check,
    delete_course_semester,
    get_active_open_period,
    get_all_authorized_users,
    get_all_bookings,
    get_audit_logs,
    get_booking_by_id,
    get_course_blocks,
    get_course_semesters,
    get_dashboard_counts,
    get_user_bookings,
    import_authorized_users,
    init_db,
    record_login,
    record_logout,
    save_open_period,
    set_course_semester_active,
    update_booking,
    verify_authorized_user_by_code,
)

BASE_DIR = Path(__file__).parent
PSY_LOGO = BASE_DIR / "assets" / "psychology_logo.jpg"
AU_LOGO = BASE_DIR / "assets" / "asia_university_logo.png"

ROOMS = ["M502", "M506", "M507", "M510", "800A"]
TIME_SLOTS = [
    ("08:10", "09:00"), ("09:10", "10:00"), ("10:10", "11:00"),
    ("11:10", "12:00"), ("12:10", "13:00"), ("13:10", "14:00"),
    ("14:10", "15:00"), ("15:10", "16:00"), ("16:10", "17:00"),
    ("17:10", "18:00"), ("18:25", "19:10"), ("19:10", "19:55"),
    ("20:00", "20:45"), ("20:50", "21:35"), ("21:35", "22:20"),
]

TEXT = {
    "中文": {
        "title1": "亞洲大學心理學系",
        "title2": "專業教室借用及查詢系統",
        "subtitle": "AU Psychology Classroom Reservation System",
        "login_title": "系統登入",
        "login_hint": "請選擇身分並輸入辨識碼",
        "faculty": "教師",
        "student": "學生",
        "admin": "管理員",
        "id_code": "教師職編／學生學號",
        "admin_password": "管理員密碼",
        "login": "登入",
        "logout": "登出",
        "home": "首頁",
        "reserve": "我要借教室",
        "query": "教室查詢",
        "admin_panel": "管理員後台",
        "invalid_user": "身分驗證失敗，僅限心理學系教師及學生使用。",
        "invalid_admin": "管理員密碼錯誤。",
        "date": "借用日期",
        "room": "教室",
        "start": "開始時間",
        "end": "結束時間",
        "phone": "聯絡手機",
        "email": "聯絡信箱",
        "reason": "借用事由",
        "submit": "送出申請",
        "available": "可借用",
        "course": "已排課",
        "reserved": "已借用",
        "privacy": "本系統僅供亞洲大學心理學系教師與學生使用，資料僅供教室借用與行政管理。",
    },
    "English": {
        "title1": "Asia University Department of Psychology",
        "title2": "Classroom Reservation and Inquiry System",
        "subtitle": "亞洲大學心理學系專業教室借用及查詢系統",
        "login_title": "System Login",
        "login_hint": "Select your role and enter your identification code",
        "faculty": "Faculty",
        "student": "Student",
        "admin": "Administrator",
        "id_code": "Employee ID / Student ID",
        "admin_password": "Administrator Password",
        "login": "Log In",
        "logout": "Log Out",
        "home": "Home",
        "reserve": "Reserve a Classroom",
        "query": "Check Availability",
        "admin_panel": "Admin Panel",
        "invalid_user": "Identity verification failed. This system is limited to Psychology faculty and students.",
        "invalid_admin": "Incorrect administrator password.",
        "date": "Reservation Date",
        "room": "Classroom",
        "start": "Start Time",
        "end": "End Time",
        "phone": "Mobile Phone",
        "email": "Email",
        "reason": "Purpose",
        "submit": "Submit",
        "available": "Available",
        "course": "Course",
        "reserved": "Reserved",
        "privacy": "This system is for Asia University Department of Psychology faculty and students only. Data is used solely for classroom reservation and administration.",
    },
}


def get_admin_password() -> str:
    try:
        if "ADMIN_PASSWORD" in st.secrets:
            return str(st.secrets["ADMIN_PASSWORD"])
        if "admin" in st.secrets and "password" in st.secrets["admin"]:
            return str(st.secrets["admin"]["password"])
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "admin123")


def valid_email(value: str) -> bool:
    return re.fullmatch(
        r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
        value.strip(),
    ) is not None


def valid_phone(value: str) -> bool:
    return len(re.sub(r"\D", "", value)) >= 8


def excel_bytes(rows: list[dict], sheet_name: str) -> bytes:
    output = io.BytesIO()
    pd.DataFrame(rows).to_excel(
        output, index=False, sheet_name=sheet_name, engine="openpyxl"
    )
    return output.getvalue()


def apply_style():
    st.markdown(
        """
        <style>
        :root { --purple:#4B2BD7; --purple-dark:#2F1A96; }
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(75,43,215,.08), transparent 28%),
                #ffffff;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg,#35188E,#5630D8);
        }
        [data-testid="stSidebar"] * { color:white !important; }
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            color:#26243A !important;
        }
        [data-testid="stSidebar"] input {
            color:#26243A !important;
            background:white !important;
        }
        .hero {
            padding:22px 28px;
            border:1px solid #E5DFFF;
            border-radius:22px;
            background:white;
            box-shadow:0 12px 34px rgba(75,43,215,.08);
        }
        .title1 {
            font-size:clamp(1.8rem,3vw,3rem);
            font-weight:850;
            color:var(--purple-dark);
            line-height:1.1;
        }
        .title2 {
            font-size:clamp(1.5rem,2.5vw,2.5rem);
            font-weight:780;
            margin-top:8px;
        }
        .subtitle { margin-top:9px; color:#6D6781; }
        .pill {
            display:inline-block;
            margin-top:10px;
            padding:5px 12px;
            border-radius:999px;
            background:#ECE7FF;
            color:#35188E;
            font-weight:700;
        }
        div[data-testid="stMetric"] {
            border:1px solid #E5DFFF;
            border-radius:16px;
            padding:14px;
            background:white;
            box-shadow:0 8px 22px rgba(75,43,215,.06);
        }
        .login-card {
            max-width:680px;
            margin:1.5rem auto .8rem auto;
            padding:1.5rem 1.8rem;
            border:1px solid #E5DFFF;
            border-radius:22px;
            background:#fff;
            box-shadow:0 16px 42px rgba(75,43,215,.10);
            text-align:center;
        }
        .login-card h2 {
            color:#2F1A96;
            margin:.1rem 0 .35rem 0;
            font-size:2rem;
        }
        .login-card p {
            color:#756F88;
            margin:0;
        }
        .user-hero {
            padding:1.15rem 1.3rem;
            border-radius:18px;
            background:linear-gradient(135deg,#F3EFFF,#FFFFFF);
            border:1px solid #E4DCFF;
            margin-bottom:1rem;
        }
        .user-hero-title {
            font-size:1.35rem;
            font-weight:800;
            color:#2F1A96;
        }
        .user-hero-sub {
            color:#726C84;
            margin-top:.25rem;
        }
        .footer {
            margin-top:2.5rem;
            padding:1.2rem;
            border-top:1px solid #E5DFFF;
            color:#777184;
            text-align:center;
            font-size:.9rem;
        }
        .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button {
            border-radius:12px;
            font-weight:700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(t):
    left, center, right = st.columns([1.1, 4.5, 1.1], vertical_alignment="center")
    with left:
        if PSY_LOGO.exists():
            st.image(str(PSY_LOGO), width=210)
    with center:
        st.markdown(
            f"""
            <div class="hero">
                <div class="title1">{t["title1"]}</div>
                <div class="title2">{t["title2"]}</div>
                <div class="subtitle">{t["subtitle"]}</div>
                <div class="pill">AU-PCRS V3.0.1 Login</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if AU_LOGO.exists():
            st.image(str(AU_LOGO), width=140)


def render_login(t):
    st.markdown(
        f"""
        <div class="login-card">
            <h2>{t["login_title"]} / System Login</h2>
            <p>{t["login_hint"]}<br>Select your role and enter your identification code</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        role = st.radio(
            "身分 / Role",
            [t["faculty"], t["student"], t["admin"]],
            horizontal=True,
        )
        credential = st.text_input(
            t["admin_password"] if role == t["admin"] else t["id_code"],
            type="password" if role == t["admin"] else "default",
        )
        submitted = st.form_submit_button(t["login"], use_container_width=True)

    if submitted:
        if role == t["admin"]:
            if credential and credential == get_admin_password():
                st.session_state.user = {
                    "user_type": "管理員",
                    "name": "Administrator",
                    "identification_code": "ADMIN",
                    "email": "",
                }
                st.session_state.is_admin = True
                record_login("管理員", "ADMIN", "Administrator", True)
                st.rerun()
            st.error(t["invalid_admin"])
        else:
            user_type = "教師" if role == t["faculty"] else "學生"
            user = verify_authorized_user_by_code(user_type, credential)
            if user:
                st.session_state.user = user
                st.session_state.is_admin = False
                record_login(
                    user["user_type"],
                    user["identification_code"],
                    user["name"],
                    True,
                )
                st.rerun()
            st.error(t["invalid_user"])
    st.caption(t["privacy"])


def render_home():
    counts = get_dashboard_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faculty / 教師", counts["teachers"])
    c2.metric("Students / 學生", counts["students"])
    c3.metric("Active / 有效借用", counts["active_bookings"])
    c4.metric("Rooms / 教室", len(ROOMS))

    period = get_active_open_period()
    if period:
        st.success(
            f'{period["semester"]}｜{period["start_date"]}～{period["end_date"]}'
        )
    else:
        st.warning("No active reservation period / 尚未設定開放期間")

    ok, message = database_health_check()
    if ok:
        st.info(f"✅ Database: {message}")
    else:
        st.error(f"❌ Database: {message}")



def render_user_dashboard(t):
    user = st.session_state.user
    my_rows = get_user_bookings(
        user["user_type"],
        user["identification_code"],
        limit=200,
    )
    today_text = str(date.today())
    today_rows = [
        row for row in my_rows
        if str(row["booking_date"]) == today_text and row["status"] == "有效"
    ]
    upcoming_rows = [
        row for row in my_rows
        if str(row["booking_date"]) >= today_text and row["status"] == "有效"
    ]

    st.markdown(
        f"""
        <div class="user-hero">
            <div class="user-hero-title">
                {t["welcome"]}，{user["name"]}
            </div>
            <div class="user-hero-sub">
                {user["user_type"]}｜{user["identification_code"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(t["my_bookings"], len(my_rows))
    c2.metric(t["today_bookings"], len(today_rows))
    c3.metric(t["upcoming_bookings"], len(upcoming_rows))

    st.markdown(f"## {t['my_bookings']}")
    if my_rows:
        view = pd.DataFrame(my_rows)[
            [
                "booking_id",
                "booking_date",
                "start_time",
                "end_time",
                "room",
                "reason",
                "status",
            ]
        ]
        view.columns = [
            "ID / 編號",
            "Date / 日期",
            "Start / 開始",
            "End / 結束",
            "Room / 教室",
            "Purpose / 用途",
            "Status / 狀態",
        ]
        st.dataframe(view, use_container_width=True, hide_index=True)
    else:
        st.info(t["no_my_bookings"])


def render_reservation(t):
    user = st.session_state.user
    st.success(f'{user["name"]}（{user["user_type"]}）')

    with st.form("booking_form"):
        left, right = st.columns(2)
        with left:
            booking_date = st.date_input(
                t["date"], value=date.today(), min_value=date.today()
            )
            room = st.selectbox(t["room"], ROOMS)
            start_time = st.selectbox(t["start"], [s for s, _ in TIME_SLOTS])
            end_time = st.selectbox(t["end"], [e for _, e in TIME_SLOTS])
        with right:
            phone = st.text_input(t["phone"])
            email = st.text_input(t["email"], value=user.get("email") or "")
            reason = st.text_area(t["reason"])

        submitted = st.form_submit_button(t["submit"], use_container_width=True)

    if not submitted:
        return

    if not phone.strip() or not email.strip() or not reason.strip():
        st.error("Please complete all required fields / 請完整填寫必填欄位")
        return
    if not valid_phone(phone) or not valid_email(email) or start_time >= end_time:
        st.error("Invalid input / 輸入格式不正確")
        return

    period = get_active_open_period()
    if not period or not (
        str(period["start_date"]) <= str(booking_date) <= str(period["end_date"])
    ):
        st.error("Outside reservation period / 不在開放期間")
        return

    conflict = check_booking_conflict(
        str(booking_date), room, start_time, end_time
    )
    if conflict:
        st.error("Time conflict / 時段衝突")
        st.caption(conflict["detail"])
        return

    booking_id = create_booking(
        str(booking_date),
        room,
        start_time,
        end_time,
        user["user_type"],
        user["name"],
        user["identification_code"],
        phone.strip(),
        email.strip(),
        reason.strip(),
    )
    st.success(f"Reservation ID / 借用編號：{booking_id}")


def render_query(t):
    left, right = st.columns(2)
    with left:
        query_date = st.date_input(t["date"], value=date.today(), key="query_date")
    with right:
        query_room = st.selectbox(t["room"], ROOMS, key="query_room")

    courses = get_course_blocks(str(query_date), query_room)
    bookings = [
        row for row in get_all_bookings()
        if str(row["booking_date"]) == str(query_date)
        and row["room"] == query_room
        and row["status"] == "有效"
    ]

    output = []
    for start, end in TIME_SLOTS:
        status, detail = t["available"], ""
        for course in courses:
            if (
                start < str(course["end_time"])[:5]
                and end > str(course["start_time"])[:5]
            ):
                status, detail = t["course"], course["course_name"]
                break
        if status == t["available"]:
            for booking in bookings:
                if (
                    start < str(booking["end_time"])[:5]
                    and end > str(booking["start_time"])[:5]
                ):
                    status, detail = t["reserved"], ""
                    break
        output.append(
            {
                "Time / 時間": f"{start}–{end}",
                "Status / 狀態": status,
                "Detail / 說明": detail,
            }
        )
    st.dataframe(pd.DataFrame(output), use_container_width=True, hide_index=True)


def render_admin():
    tabs = st.tabs(
        [
            "Dashboard",
            "Roster / 名冊",
            "Open Period / 開放期間",
            "Schedule / 課表",
            "Bookings / 借用管理",
            "Audit / 操作紀錄",
        ]
    )

    with tabs[0]:
        render_home()

    with tabs[1]:
        user_type = st.radio("名冊類別", ["教師", "學生"], horizontal=True)
        upload = st.file_uploader(
            "Excel：辨識碼、姓名、聯絡信箱、狀態",
            type=["xlsx"],
            key="roster_upload",
        )
        replace = st.checkbox("覆蓋此類名冊")
        if st.button("匯入名冊"):
            if upload is None:
                st.error("請先選擇檔案")
            else:
                result = import_authorized_users(
                    pd.read_excel(upload, dtype=str).fillna(""),
                    user_type,
                    replace,
                )
                st.success(result)

        rows = get_all_authorized_users()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tabs[2]:
        left, right = st.columns(2)
        with left:
            start_date = st.date_input("開始日期", value=date.today(), key="period_start")
        with right:
            end_date = st.date_input("結束日期", value=date.today(), key="period_end")
        semester = st.text_input("學期", value="115-1")

        if st.button("儲存並啟用"):
            if start_date > end_date:
                st.error("開始日期不可晚於結束日期。")
            else:
                save_open_period(semester, str(start_date), str(end_date))
                st.success("已儲存")

    with tabs[3]:
        semester = st.text_input("匯入學期", value="115-1", key="course_semester")
        replace = st.checkbox("清除此學期既有課表")
        upload = st.file_uploader("課表 Excel", type=["xlsx"], key="course_upload")

        if upload is not None:
            frame = pd.read_excel(upload, dtype=str).fillna("")
            st.dataframe(frame.head(20), use_container_width=True, hide_index=True)
            if st.button("確認匯入課表"):
                st.success(add_course_blocks(frame, semester, replace))

        semester_rows = get_course_semesters()
        if semester_rows:
            st.dataframe(
                pd.DataFrame(semester_rows),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[4]:
        rows = get_all_bookings()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.download_button(
                "匯出 Excel",
                excel_bytes(rows, "借用紀錄"),
                f"bookings_{date.today()}.xlsx",
            )

            booking_id = st.selectbox(
                "借用編號", [row["booking_id"] for row in rows]
            )
            item = get_booking_by_id(booking_id)
            if item:
                cancel_reason = st.text_input("取消原因")
                if st.button("取消借用"):
                    if not cancel_reason.strip():
                        st.error("請輸入取消原因")
                    else:
                        cancel_booking(booking_id, cancel_reason.strip())
                        st.rerun()
        else:
            st.info("目前尚無借用紀錄")

    with tabs[5]:
        logs = get_audit_logs()
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無操作紀錄")



def render_footer():
    st.markdown(
        """
        <div class="footer">
            Asia University Department of Psychology<br>
            © 2026 AU-PCRS Cloud System
        </div>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="AU-PCRS", layout="wide")
apply_style()

for key, default in {
    "language": "中文",
    "user": None,
    "is_admin": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

try:
    init_db()
except Exception as exc:
    st.error("Database initialization failed / 資料庫初始化失敗")
    st.caption(str(exc))
    st.stop()

language = st.sidebar.selectbox(
    "語言 / Language",
    ["中文", "English"],
    index=0 if st.session_state.language == "中文" else 1,
)
st.session_state.language = language
t = TEXT[language]
render_header(t)

if st.session_state.user is None:
    render_login(t)
    render_footer()
    st.stop()

with st.sidebar:
    st.markdown(f'### {st.session_state.user["name"]}')
    if st.button(t["logout"], use_container_width=True):
        current_user = st.session_state.user
        record_logout(
            current_user["user_type"],
            current_user["identification_code"],
            current_user["name"],
        )
        st.session_state.user = None
        st.session_state.is_admin = False
        st.rerun()

page = st.sidebar.radio(
    "Menu / 選單",
    [t["home"], t["admin_panel"]]
    if st.session_state.is_admin
    else [t["home"], t["my_bookings"], t["reserve"], t["query"]],
)

if page == t["home"]:
    render_home()
elif page == t["reserve"]:
    render_reservation(t)
elif page == t["query"]:
    render_query(t)
else:
    render_admin()

render_footer()
