import html
import io
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from database import (
    add_course_blocks, cancel_booking, check_booking_conflict, create_booking,
    database_health_check, delete_announcement, delete_authorized_user,
    delete_classroom, delete_closure, delete_course_semester,
    get_active_open_period, get_all_authorized_users, get_all_bookings,
    get_announcements, get_audit_logs, get_booking_by_id, get_classrooms,
    get_closures, get_course_blocks, get_course_semesters, get_dashboard_counts,
    get_setting, get_user_bookings, get_room_statuses, get_booking_statistics, get_week_schedule, get_ai_insight_data, get_monthly_booking_counts, search_system_records, find_available_rooms, get_usage_heatmap, get_room_utilization, forecast_room_demand, get_approval_recommendation, get_tv_dashboard_data, import_authorized_users, init_db,
    record_login, record_logout, review_booking, save_announcement, update_announcement_bilingual,
    save_classroom, save_closure, save_open_period, set_course_semester_active,
    set_setting, verify_authorized_user_by_code,
)
from notifications import send_booking_email
from reports import booking_pdf, booking_qr_png
from translation import translate_zh_to_en

BASE_DIR = Path(__file__).parent
PSY_LOGO = BASE_DIR / "assets" / "psychology_logo.jpg"
AU_LOGO = BASE_DIR / "assets" / "asia_university_logo.png"

TIME_SLOTS = [
    ("08:10", "09:00"), ("09:10", "10:00"), ("10:10", "11:00"),
    ("11:10", "12:00"), ("12:10", "13:00"), ("13:10", "14:00"),
    ("14:10", "15:00"), ("15:10", "16:00"), ("16:10", "17:00"),
    ("17:10", "18:00"), ("18:25", "19:10"), ("19:10", "19:55"),
    ("20:00", "20:45"), ("20:50", "21:35"), ("21:35", "22:20"),
]

TEXT = {
    "中文": {
        "title1":"亞洲大學心理學系","title2":"專業教室借用及查詢系統",
        "subtitle":"AU Psychology Classroom Reservation System",
        "login_title":"系統登入","faculty":"教師","student":"學生","admin":"管理員",
        "id_code":"教師職編／學生學號","admin_password":"管理員密碼",
        "login":"登入","logout":"登出","home":"首頁","my_bookings":"我的借用",
        "reserve":"我要借教室","calendar":"教室行事曆","weekly":"視覺化週課表","ai_assistant":"AI 智慧助理","tv_mode":"TV 營運看板","admin_panel":"管理員後台",
        "invalid_user":"身分驗證失敗，請確認名冊與辨識碼。","invalid_admin":"管理員密碼錯誤。",
        "date":"借用日期","room":"教室","start":"開始時間","end":"結束時間",
        "phone":"聯絡手機","email":"聯絡信箱","reason":"借用事由","submit":"送出申請",
        "available":"可借用","course":"已排課","reserved":"已借用","closed":"停借",
        "privacy":"本系統僅供亞洲大學心理學系教師與學生使用。",
        "welcome":"歡迎使用","pending":"待審核","approved":"已核准",
    },
    "English": {
        "title1":"Asia University Department of Psychology",
        "title2":"Classroom Reservation and Inquiry System",
        "subtitle":"亞洲大學心理學系專業教室借用及查詢系統",
        "login_title":"System Login","faculty":"Faculty","student":"Student","admin":"Administrator",
        "id_code":"Employee ID / Student ID","admin_password":"Administrator Password",
        "login":"Log In","logout":"Log Out","home":"Home","my_bookings":"My Reservations",
        "reserve":"Reserve a Classroom","calendar":"Classroom Calendar","weekly":"Weekly Schedule","ai_assistant":"AI Assistant","tv_mode":"TV Operations Board","admin_panel":"Admin Panel",
        "invalid_user":"Identity verification failed. Please check the roster and code.",
        "invalid_admin":"Incorrect administrator password.","date":"Reservation Date",
        "room":"Classroom","start":"Start Time","end":"End Time","phone":"Mobile Phone",
        "email":"Email","reason":"Purpose","submit":"Submit","available":"Available",
        "course":"Course","reserved":"Reserved","closed":"Closed",
        "privacy":"This system is for Asia University Department of Psychology faculty and students only.",
        "welcome":"Welcome","pending":"Pending","approved":"Approved",
    }
}


def admin_password():
    try:
        if "ADMIN_PASSWORD" in st.secrets:
            return str(st.secrets["ADMIN_PASSWORD"])
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "admin123")


def valid_email(value):
    return re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", value.strip()) is not None


def valid_phone(value):
    return len(re.sub(r"\D", "", value)) >= 8


def excel_bytes(rows, sheet_name, columns=None):
    """Export rows safely to Excel.

    PostgreSQL timestamptz values are timezone-aware. Excel cannot write
    timezone-aware datetimes, so this helper converts them to readable strings.
    It also supports exporting an empty table with predefined columns.
    """
    output = io.BytesIO()
    frame = pd.DataFrame(rows)

    if frame.empty and columns:
        frame = pd.DataFrame(columns=columns)

    for column in frame.columns:
        series = frame[column]

        # Handle pandas datetime dtypes, including timezone-aware timestamps.
        if pd.api.types.is_datetime64_any_dtype(series):
            try:
                if getattr(series.dt, "tz", None) is not None:
                    frame[column] = series.dt.tz_convert(None)
            except (AttributeError, TypeError):
                pass

        # Handle object columns containing Python datetime/time/date objects.
        if frame[column].dtype == "object":
            frame[column] = frame[column].map(
                lambda value: (
                    value.isoformat(sep=" ", timespec="seconds")
                    if isinstance(value, datetime)
                    else value.isoformat()
                    if isinstance(value, date)
                    else value.strftime("%H:%M:%S")
                    if hasattr(value, "strftime") and value.__class__.__name__ == "time"
                    else value
                )
            )

    frame.to_excel(
        output,
        index=False,
        sheet_name=str(sheet_name)[:31] or "資料",
        engine="openpyxl",
    )
    return output.getvalue()


def roster_template_bytes(user_type):
    if user_type == "教師":
        frame = pd.DataFrame([{"教師職編":"T0001","姓名":"測試教師","聯絡信箱":"teacher@example.com","狀態":"啟用"}])
    else:
        frame = pd.DataFrame([{"學生學號":"910300510","姓名":"測試學生","聯絡信箱":"student@example.com","狀態":"啟用"}])
    output = io.BytesIO()
    frame.to_excel(output, index=False, sheet_name=user_type)
    return output.getvalue()


def apply_style():
    st.markdown("""
    <style>
    :root{--p:#4B2BD7;--pd:#2F1A96}
    .stApp{background:radial-gradient(circle at top right,rgba(75,43,215,.10),transparent 28%),#fff}
    [data-testid=stSidebar]{background:linear-gradient(180deg,#35188E,#5630D8)}
    [data-testid=stSidebar] *{color:white!important}
    [data-testid=stSidebar] [data-baseweb=select] *{color:#26243A!important}
    [data-testid=stSidebar] input{color:#26243A!important;background:white!important}
    [data-testid=stSidebar] .stButton > button{
        background:#ffffff!important;
        color:#35188E!important;
        border:1px solid rgba(255,255,255,.65)!important;
        font-weight:800!important;
        opacity:1!important;
    }
    [data-testid=stSidebar] .stButton > button *{
        color:#35188E!important;
        opacity:1!important;
    }
    [data-testid=stSidebar] .stButton > button:hover{
        background:#F2EEFF!important;
        color:#2F1A96!important;
        border-color:#D9CEFF!important;
    }
    [data-testid=stSidebar] .stButton > button:focus,
    [data-testid=stSidebar] .stButton > button:active{
        background:#E8E0FF!important;
        color:#2F1A96!important;
        border-color:#CFC0FF!important;
        box-shadow:0 0 0 2px rgba(255,255,255,.25)!important;
    }
    [data-testid=stSidebar] .stButton > button:disabled{
        background:#ffffff!important;
        color:#35188E!important;
        opacity:1!important;
    }
    .hero{padding:22px 28px;border:1px solid #e5dfff;border-radius:22px;background:#fff;box-shadow:0 12px 34px rgba(75,43,215,.08)}
    .h1{font-size:clamp(1.8rem,3vw,3rem);font-weight:850;color:var(--pd);line-height:1.1}
    .h2{font-size:clamp(1.5rem,2.5vw,2.5rem);font-weight:780;margin-top:8px}
    .sub{margin-top:9px;color:#6d6781}.pill{display:inline-block;margin-top:10px;padding:5px 12px;border-radius:999px;background:#ece7ff;color:#35188e;font-weight:700}
    .login-card,.panel{padding:1.4rem;border:1px solid #e5dfff;border-radius:18px;background:#fff;box-shadow:0 10px 28px rgba(75,43,215,.07)}
    .announcement{padding:.85rem 1rem;border-left:5px solid #4B2BD7;background:#F6F3FF;border-radius:10px;margin-bottom:.6rem}
    .room-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:12px 0 24px 0}
    .room-v5{padding:18px;border:1px solid #e5dfff;border-radius:18px;background:white;box-shadow:0 8px 22px rgba(75,43,215,.06)}
    .room-v5-name{font-size:1.25rem;font-weight:800;color:#35188E}
    .room-v5-status{font-weight:750;margin-top:10px}
    .status-free{color:#14833B}.status-busy{color:#E06700}.status-course{color:#1768D8}.status-closed{color:#C62828}
    .kpi-note{font-size:.86rem;color:#777184;margin-top:4px}
    .ai-card{padding:20px;border:1px solid #dcd2ff;border-radius:18px;background:linear-gradient(135deg,#f4f0ff,#fff);box-shadow:0 8px 24px rgba(75,43,215,.08);margin-bottom:14px}
    .ai-title{font-size:1.25rem;font-weight:850;color:#35188E}
    .ai-insight{padding:12px 14px;border-left:5px solid #4B2BD7;background:#fff;border-radius:10px;margin:9px 0}
    .search-result{padding:12px 14px;border:1px solid #e5dfff;border-radius:12px;background:#fff;margin-bottom:9px}
    .tv-board{background:#111827;color:white;padding:24px;border-radius:22px}
    .tv-title{font-size:2rem;font-weight:900;margin-bottom:16px}
    .tv-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
    .tv-card{background:#1F2937;padding:18px;border-radius:16px;border:1px solid #374151}
    .tv-card h3{margin:0 0 10px 0;color:#C4B5FD}
    @media (max-width:768px){
      .hero{padding:16px}.h1{font-size:1.7rem}.h2{font-size:1.35rem}
      .room-grid{grid-template-columns:1fr}
    }
    div[data-testid=stMetric]{border:1px solid #e5dfff;border-radius:16px;padding:14px;background:#fff;box-shadow:0 8px 22px rgba(75,43,215,.06)}
    .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700}
    .footer{margin-top:2rem;padding:1rem;border-top:1px solid #e5dfff;color:#777;text-align:center}
    </style>
    """, unsafe_allow_html=True)


def header(t):
    left, center, right = st.columns([1.3,4.6,1.3], vertical_alignment="center")
    with left:
        if PSY_LOGO.exists(): st.image(str(PSY_LOGO), width=210)
    with center:
        st.markdown(f'<div class="hero"><div class="h1">{t["title1"]}</div><div class="h2">{t["title2"]}</div><div class="sub">{t["subtitle"]}</div><div class="pill">AU-PCRS V7.0.2 Auto Translation</div></div>', unsafe_allow_html=True)
    with right:
        if AU_LOGO.exists(): st.image(str(AU_LOGO), width=170)


def footer():
    st.markdown('<div class="footer">Asia University Department of Psychology<br>© 2026 AU-PCRS Enterprise</div>', unsafe_allow_html=True)


def login(t):
    st.markdown(
        f'<div class="login-card"><h2>{t["login_title"]} / System Login</h2></div>',
        unsafe_allow_html=True,
    )

    roles = [t["faculty"], t["student"], t["admin"]]

    # 身分選擇必須放在 form 外。
    # Streamlit form 會將元件變更延後到送出時才同步；
    # 若 role 放在 form 內，第一次按登入只會套用「管理員」身分，
    # 第二次才真正送出管理員密碼。
    role = st.radio(
        "身分 / Role",
        roles,
        horizontal=True,
        key="login_role",
    )

    is_admin_role = role == t["admin"]
    field_label = (
        t["admin_password"]
        if is_admin_role
        else t["id_code"]
    )
    field_type = "password" if is_admin_role else "default"

    with st.form("login_form", clear_on_submit=False):
        credential = st.text_input(
            field_label,
            type=field_type,
            key=f"login_credential_{'admin' if is_admin_role else 'user'}",
        )
        submitted = st.form_submit_button(
            t["login"],
            use_container_width=True,
        )

    if submitted:
        credential = credential.strip()

        if is_admin_role:
            if credential and credential == admin_password():
                st.session_state.user = {
                    "user_type": "管理員",
                    "name": "Administrator",
                    "identification_code": "ADMIN",
                    "email": "",
                }
                st.session_state.admin = True
                record_login("管理員", "ADMIN", "Administrator", True)
                st.rerun()

            record_login("管理員", "ADMIN", "Administrator", False)
            st.error(t["invalid_admin"])
        else:
            kind = "教師" if role == t["faculty"] else "學生"
            user = verify_authorized_user_by_code(kind, credential)

            if user:
                st.session_state.user = user
                st.session_state.admin = False
                record_login(
                    user["user_type"],
                    user["identification_code"],
                    user["name"],
                    True,
                )
                st.rerun()

            record_login(kind, credential, "", False)
            st.error(t["invalid_user"])

    st.caption(t["privacy"])


def announcements_block():
    items = get_announcements(active_only=True)
    if items:
        st.markdown("### 最新公告 / Announcements")
        for item in items:
            title_zh = html.escape(str(item.get("title") or ""))
            content_zh = html.escape(
                str(item.get("content") or "")
            ).replace("\n", "<br>")
            title_en = html.escape(
                str(item.get("title_en") or "")
            )
            content_en = html.escape(
                str(item.get("content_en") or "")
            ).replace("\n", "<br>")

            english_section = (
                f'<div style="margin-top:10px;padding-top:10px;'
                f'border-top:1px solid #d9d2ff;">'
                f'<b>{title_en}</b><br>{content_en}</div>'
                if title_en and content_en
                else (
                    '<div style="margin-top:10px;padding-top:10px;'
                    'border-top:1px solid #d9d2ff;color:#7a748a;">'
                    '<b>English</b><br>'
                    'English translation has not been added yet.'
                    '</div>'
                )
            )

            st.markdown(
                '<div class="announcement">'
                f'<b>{title_zh}</b><br>{content_zh}'
                f'{english_section}'
                '</div>',
                unsafe_allow_html=True,
            )



def room_status_dashboard():
    st.markdown("### 教室即時狀態 / Live Classroom Status")
    room_rows = get_room_statuses()
    if not room_rows:
        st.info("目前沒有啟用中的教室。")
        return

    class_map = {
        "可借用": "status-free",
        "使用中": "status-busy",
        "上課中": "status-course",
        "停借": "status-closed",
    }
    parts = ['<div class="room-grid">']

    for row in room_rows:
        status_class = class_map.get(row["status"], "status-busy")
        time_text = ""
        if row.get("start_time") and row.get("end_time"):
            time_text = (
                '<div class="kpi-note">'
                + str(row["start_time"])[:5]
                + "–"
                + str(row["end_time"])[:5]
                + "</div>"
            )

        detail_text = ""
        if row.get("detail"):
            detail_text = (
                '<div class="kpi-note">'
                + str(row["detail"])
                + "</div>"
            )

        parts.append(
            '<div class="room-v5">'
            + '<div class="room-v5-name">'
            + str(row["room_name"])
            + "</div>"
            + '<div class="room-v5-status '
            + status_class
            + '">'
            + str(row["status"])
            + "</div>"
            + time_text
            + detail_text
            + "</div>"
        )

    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def analytics_dashboard(key_prefix):
    st.markdown("### 使用統計 / Usage Analytics")
    period_days = st.selectbox(
        "統計期間",
        [7, 30, 90, 180, 365],
        index=1,
        format_func=lambda value: f"最近 {value} 天",
        key=f"{key_prefix}_analytics_days",
    )
    stats = get_booking_statistics(period_days)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("總申請 / Total", stats["total"])
    c2.metric("已核准 / Approved", stats["approved"])
    c3.metric("待審核 / Pending", stats["pending"])
    c4.metric("取消或退回 / Cancelled", stats["cancelled"])

    left, right = st.columns(2)
    with left:
        st.markdown("#### 熱門教室")
        if stats["by_room"]:
            st.bar_chart(pd.DataFrame(stats["by_room"]).set_index("room"))
        else:
            st.info("目前沒有統計資料。")

    with right:
        st.markdown("#### 借用狀態")
        if stats["by_status"]:
            st.bar_chart(pd.DataFrame(stats["by_status"]).set_index("status"))
        else:
            st.info("目前沒有統計資料。")

    st.markdown("#### 每日借用趨勢")
    if stats["by_date"]:
        st.line_chart(pd.DataFrame(stats["by_date"]).set_index("date"))
    else:
        st.info("目前沒有統計資料。")


def weekly_schedule_view(t, key_prefix):
    st.markdown("## 視覺化週課表 / Weekly Schedule")
    room_options = [
        row["room_name"] for row in get_classrooms(active_only=True)
    ]
    if not room_options:
        st.info("目前沒有啟用中的教室。")
        return

    today = date.today()
    monday = today - timedelta(days=today.weekday())

    left, right = st.columns(2)
    with left:
        week_start = st.date_input(
            "週起始日（星期一）",
            value=monday,
            key=f"{key_prefix}_week_start",
        )
    with right:
        selected_room = st.selectbox(
            t["room"],
            room_options,
            key=f"{key_prefix}_week_room",
        )

    schedule_rows = get_week_schedule(str(week_start), selected_room)
    if not schedule_rows:
        st.success("本週沒有課程或借用紀錄。")
        return

    schedule_frame = pd.DataFrame(schedule_rows)
    schedule_frame.columns = [
        "日期 / Date",
        "開始 / Start",
        "結束 / End",
        "類型 / Type",
        "名稱 / Title",
        "狀態 / Status",
    ]
    st.dataframe(
        schedule_frame,
        use_container_width=True,
        hide_index=True,
    )



def build_ai_insights(days=30):
    data = get_ai_insight_data(days)
    stats = data["statistics"]
    insights = []

    if stats["total"] == 0:
        insights.append("最近選定期間尚無借用資料，建議先完成課表與借用資料匯入。")
        return insights

    approval_rate = (
        stats["approved"] / stats["total"] * 100
        if stats["total"]
        else 0
    )
    pending_rate = (
        stats["pending"] / stats["total"] * 100
        if stats["total"]
        else 0
    )

    insights.append(
        f'最近 {days} 天共有 {stats["total"]} 筆申請，'
        f'核准或完成比例約 {approval_rate:.1f}%。'
    )

    if data["peak_room"]:
        insights.append(
            f'使用最頻繁的教室是 {data["peak_room"]["room"]}，'
            f'共 {data["peak_room"]["count"]} 筆紀錄。'
        )

    if data["peak_date"]:
        insights.append(
            f'借用量最高的日期為 {data["peak_date"]["date"]}，'
            f'共有 {data["peak_date"]["count"]} 筆。'
        )

    if pending_rate >= 25:
        insights.append(
            f'待審核比例達 {pending_rate:.1f}%，建議系辦優先處理待審核案件。'
        )
    elif stats["pending"] == 0:
        insights.append("目前沒有待審核案件，審核流程維持順暢。")

    if data["free_rooms_now"]:
        insights.append(
            f'目前共有 {data["free_rooms_now"]} 間教室可借用，'
            f'{data["busy_rooms_now"]} 間正在使用、上課或停借。'
        )
    else:
        insights.append("目前沒有可立即借用的教室，建議查詢其他時段。")

    monthly = get_monthly_booking_counts(6)
    if len(monthly) >= 2:
        latest = monthly[-1]
        previous = monthly[-2]
        if previous["count"] > 0:
            change = (
                (latest["count"] - previous["count"])
                / previous["count"]
                * 100
            )
            direction = "增加" if change >= 0 else "減少"
            insights.append(
                f'{latest["month"]} 相較 {previous["month"]} '
                f'借用量{direction} {abs(change):.1f}%。'
            )

    return insights


def ai_insight_panel(key_prefix):
    st.markdown("## AI 智慧分析 / AI Insights")
    days = st.selectbox(
        "分析期間",
        [7, 30, 90, 180, 365],
        index=1,
        format_func=lambda value: f"最近 {value} 天",
        key=f"{key_prefix}_ai_days",
    )
    insights = build_ai_insights(days)

    st.markdown(
        '<div class="ai-card"><div class="ai-title">'
        'AU-PCRS 智慧營運摘要'
        '</div></div>',
        unsafe_allow_html=True,
    )
    for insight in insights:
        st.markdown(
            f'<div class="ai-insight">{insight}</div>',
            unsafe_allow_html=True,
        )


def smart_search_panel(key_prefix):
    st.markdown("## 智慧搜尋 / Smart Search")
    keyword = st.text_input(
        "輸入借用編號、姓名、學號、教室、用途或公告關鍵字",
        key=f"{key_prefix}_smart_search",
    )
    if not keyword.strip():
        st.caption("例如：M502、王小明、910300510、心理統計、已核准")
        return

    results = search_system_records(keyword, limit=100)
    if not results:
        st.info("找不到符合條件的資料。")
        return

    st.success(f"找到 {len(results)} 筆結果")
    for result in results:
        st.markdown(
            '<div class="search-result">'
            f'<b>{result["category"]}｜{result["title"]}</b><br>'
            f'{result["summary"]}'
            '</div>',
            unsafe_allow_html=True,
        )


def availability_assistant(t, key_prefix):
    st.markdown("## AI 空間推薦 / Smart Availability Assistant")
    st.caption("選擇日期與時段，系統會自動排除課程、借用與停借教室。")

    left, middle, right = st.columns(3)
    with left:
        target_date = st.date_input(
            t["date"],
            value=date.today(),
            key=f"{key_prefix}_available_date",
        )
    with middle:
        start_value = st.selectbox(
            t["start"],
            [start for start, _ in TIME_SLOTS],
            key=f"{key_prefix}_available_start",
        )
    with right:
        end_value = st.selectbox(
            t["end"],
            [end for _, end in TIME_SLOTS],
            key=f"{key_prefix}_available_end",
        )

    if start_value >= end_value:
        st.warning("結束時間必須晚於開始時間。")
        return

    available = find_available_rooms(
        str(target_date),
        start_value,
        end_value,
    )
    if not available:
        st.error("此時段沒有可借用的教室。")
        return

    st.success(f"找到 {len(available)} 間可借用教室")
    st.dataframe(
        pd.DataFrame(available),
        use_container_width=True,
        hide_index=True,
    )


def ai_assistant_page(t):
    st.markdown("## AU-PCRS V7 AI 智慧助理")
    ai_pro_center(t, "user_ai_pro")


def home(t):
    announcements_block()
    counts = get_dashboard_counts()
    cols = st.columns(5)
    cols[0].metric("Faculty / 教師", counts["teachers"])
    cols[1].metric("Students / 學生", counts["students"])
    cols[2].metric("Today / 今日", counts["today"])
    cols[3].metric("Pending / 待審核", counts["pending"])
    cols[4].metric("Active / 有效", counts["active_bookings"])
    period = get_active_open_period()
    if period:
        st.success(
            f'{period["semester"]}｜'
            f'{period["start_date"]}～{period["end_date"]}'
        )
    else:
        st.warning("No active reservation period / 尚未設定開放期間")

    room_status_dashboard()
    analytics_dashboard("home")
    ai_insight_panel("home")


def my_bookings(t):
    user = st.session_state.user
    rows = get_user_bookings(user["user_type"], user["identification_code"])
    st.markdown(f"## {t['my_bookings']}")
    if not rows:
        st.info("No reservations / 目前尚無借用紀錄")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    selected = st.selectbox("Reservation ID / 借用編號", [r["booking_id"] for r in rows])
    item = get_booking_by_id(selected)
    c1,c2 = st.columns(2)
    c1.download_button("下載 PDF / Download PDF", booking_pdf(item), f"{selected}.pdf", "application/pdf")
    c2.download_button("下載 QR Code", booking_qr_png(item), f"{selected}.png", "image/png")
    if item["status"] in {"待審核","已核准","有效"}:
        reason = st.text_input("取消原因 / Cancellation reason")
        if st.button("取消借用 / Cancel"):
            if reason.strip():
                cancel_booking(selected, reason.strip())
                email_ok, email_message = send_booking_email(
                    item["email"],
                    "AU-PCRS Cancellation",
                    f"Your reservation {selected} has been cancelled.",
                )
                if not email_ok and email_message != "SMTP secrets not configured":
                    st.warning(f"借用已取消，但 Email 寄送失敗：{email_message}")
                st.rerun()
            else:
                st.error("請輸入取消原因。")


def reserve(t):
    user = st.session_state.user
    rooms = [r["room_name"] for r in get_classrooms(active_only=True)]
    with st.form("reserve"):
        a,b = st.columns(2)
        with a:
            booking_date = st.date_input(t["date"], value=date.today(), min_value=date.today())
            room = st.selectbox(t["room"], rooms)
            start = st.selectbox(t["start"], [s for s,_ in TIME_SLOTS])
            end = st.selectbox(t["end"], [e for _,e in TIME_SLOTS])
        with b:
            phone = st.text_input(t["phone"])
            email = st.text_input(t["email"], value=user.get("email") or "")
            reason = st.text_area(t["reason"])
        submitted = st.form_submit_button(t["submit"], use_container_width=True)
    if not submitted: return
    if not phone.strip() or not email.strip() or not reason.strip():
        st.error("請完整填寫必填欄位。"); return
    if not valid_email(email) or not valid_phone(phone) or start >= end:
        st.error("輸入格式不正確。"); return
    period = get_active_open_period()
    if not period or not (str(period["start_date"]) <= str(booking_date) <= str(period["end_date"])):
        st.error("不在開放借用期間。"); return
    max_days = int(get_setting("max_days_ahead","180"))
    if booking_date > date.today() + timedelta(days=max_days):
        st.error(f"最多只能預約未來 {max_days} 天。"); return
    conflict = check_booking_conflict(str(booking_date),room,start,end)
    if conflict:
        st.error("無法借用：時段衝突或停借。"); st.caption(conflict["detail"]); return
    booking_id,status = create_booking(
        str(booking_date),room,start,end,user["user_type"],user["name"],
        user["identification_code"],phone.strip(),email.strip(),reason.strip()
    )
    st.success(f"借用編號：{booking_id}｜狀態：{status}")
    email_ok, email_message = send_booking_email(
        email,
        "AU-PCRS Reservation",
        f"Reservation {booking_id} submitted. Status: {status}",
    )
    if not email_ok and email_message != "SMTP secrets not configured":
        st.warning(f"借用已建立，但 Email 寄送失敗：{email_message}")


def calendar_view(t):
    rooms = [r["room_name"] for r in get_classrooms(active_only=True)]
    a,b = st.columns(2)
    with a: day = st.date_input(t["date"], value=date.today(), key="calendar_day")
    with b: room = st.selectbox(t["room"], rooms, key="calendar_room")
    courses = get_course_blocks(str(day), room)
    bookings = [r for r in get_all_bookings({"room":room,"date_from":str(day),"date_to":str(day)}) if r["status"] in {"待審核","已核准","有效"}]
    output=[]
    for start,end in TIME_SLOTS:
        status,detail=t["available"],""
        for course in courses:
            if start < str(course["end_time"])[:5] and end > str(course["start_time"])[:5]:
                status,detail=t["course"],course["course_name"]; break
        if status==t["available"]:
            for booking in bookings:
                if start < str(booking["end_time"])[:5] and end > str(booking["start_time"])[:5]:
                    status,detail=t["reserved"],booking["status"]; break
        output.append({"Time / 時間":f"{start}–{end}","Status / 狀態":status,"Detail / 說明":detail})
    st.dataframe(pd.DataFrame(output),use_container_width=True,hide_index=True)


def admin_panel():
    tabs=st.tabs([
        "Dashboard",
        "AI Center / AI 智慧中心",
        "Analytics / 統計分析",
        "Roster / 名冊",
        "Classrooms / 教室",
        "Open Period / 開放期間",
        "Schedule / 課表",
        "Booking Review / 借用審核",
        "Announcements / 公告",
        "Closures / 停借",
        "Settings / 設定",
        "Audit / 操作紀錄",
    ])
    with tabs[0]:
        home(TEXT[st.session_state.language])
    with tabs[1]:
        ai_pro_center(
            TEXT[st.session_state.language],
            "admin_ai_pro",
        )
    with tabs[2]:
        analytics_dashboard("admin_analytics")
        weekly_schedule_view(
            TEXT[st.session_state.language],
            "admin_analytics",
        )
    with tabs[3]:
        kind=st.radio("名冊類別",["教師","學生"],horizontal=True)
        st.download_button("下載範本",roster_template_bytes(kind),f"{kind}名冊範本.xlsx")
        upload=st.file_uploader("上傳 Excel",type=["xlsx"],key=f"roster_{kind}")
        mode=st.radio("匯入模式",["合併更新","覆蓋名冊"],horizontal=True)
        if upload is not None:
            preview=pd.read_excel(upload,dtype=str).fillna("")
            st.dataframe(preview.head(30),use_container_width=True,hide_index=True)
        if st.button("開始匯入"):
            if upload is None: st.error("請選擇檔案")
            else:
                result=import_authorized_users(pd.read_excel(upload,dtype=str).fillna(""),kind,mode=="覆蓋名冊")
                st.success(result); st.rerun()
        rows=get_all_authorized_users()
        if rows:
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            st.download_button(
                "匯出名冊",
                excel_bytes(
                    rows,
                    "名冊",
                    columns=[
                        "id", "user_type", "identification_code", "name",
                        "email", "status", "imported_at",
                    ],
                ),
                f"authorized_users_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("目前尚未匯入教師或學生名冊。")
    with tabs[4]:
        st.markdown("## 教室管理")
        existing=get_classrooms()
        st.dataframe(pd.DataFrame(existing),use_container_width=True,hide_index=True)
        room_name=st.text_input("教室名稱")
        capacity=st.number_input("容量",min_value=1,value=40)
        location=st.text_input("位置")
        equipment=st.text_area("設備")
        status=st.radio("狀態",["啟用","停用"],horizontal=True)
        if st.button("新增或更新教室"):
            if room_name.strip():
                save_classroom(room_name.strip(),capacity,location,equipment,status); st.rerun()
    with tabs[5]:
        a,b=st.columns(2)
        with a: sd=st.date_input("開始日期",value=date.today(),key="period_sd")
        with b: ed=st.date_input("結束日期",value=date.today(),key="period_ed")
        semester=st.text_input("學期",value="115-1")
        if st.button("儲存開放期間"):
            if sd > ed:
                st.error("開始日期不可晚於結束日期。")
            elif not semester.strip():
                st.error("請輸入學期。")
            else:
                save_open_period(semester.strip(), str(sd), str(ed))
                st.success("已儲存")
    with tabs[6]:
        semester=st.text_input("匯入學期",value="115-1",key="course_sem")
        replace=st.checkbox("清除此學期既有課表")
        upload=st.file_uploader("課表 Excel",type=["xlsx"],key="course_file")
        if upload is not None:
            frame=pd.read_excel(upload,dtype=str).fillna(""); st.dataframe(frame.head(30),use_container_width=True,hide_index=True)
            if st.button("匯入課表"): st.success(add_course_blocks(frame,semester,replace)); st.rerun()
        semesters=get_course_semesters()
        if semesters: st.dataframe(pd.DataFrame(semesters),use_container_width=True,hide_index=True)
    with tabs[7]:
        c1,c2,c3,c4=st.columns(4)
        with c1: status_filter=st.selectbox("狀態",["","待審核","已核准","已退回","已取消","已完成"])
        with c2: room_filter=st.selectbox("教室",[""]+[r["room_name"] for r in get_classrooms()])
        with c3: df=st.date_input("起日",value=date.today()-timedelta(days=30),key="review_from")
        with c4: dt=st.date_input("迄日",value=date.today()+timedelta(days=180),key="review_to")
        keyword=st.text_input("關鍵字")
        rows=get_all_bookings({"status":status_filter,"room":room_filter,"date_from":str(df),"date_to":str(dt),"keyword":keyword})
        if rows:
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            st.download_button(
                "匯出借用紀錄",
                excel_bytes(rows, "借用紀錄"),
                f"bookings_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            selected=st.selectbox("借用編號",[r["booking_id"] for r in rows])
            new_status=st.selectbox("審核結果",["已核准","已退回","已取消","已完成"])
            note=st.text_area("審核備註")
            if st.button("儲存審核結果", key="booking_review_submit"):
                try:
                    updated = review_booking(
                        selected,
                        new_status,
                        "Administrator",
                        note,
                    )
                    if not updated:
                        st.warning("找不到指定借用紀錄，未進行更新。")
                    else:
                        item = get_booking_by_id(selected)
                        if item and item.get("email"):
                            email_ok, email_message = send_booking_email(
                                item["email"],
                                "AU-PCRS Review",
                                (
                                    f"Reservation {selected}: "
                                    f"{new_status}\n{note or ''}"
                                ),
                            )
                            if (
                                not email_ok
                                and email_message
                                != "SMTP secrets not configured"
                            ):
                                st.warning(
                                    "審核結果已儲存，但 Email 寄送失敗："
                                    f"{email_message}"
                                )
                        st.success(f"借用編號 {selected} 已更新為「{new_status}」。")
                        st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error(
                        "審核資料儲存失敗。請重新整理頁面後再試；"
                        "若持續發生，請查看 Streamlit Logs。"
                    )
        else: st.info("查無借用紀錄")
    with tabs[8]:
        st.markdown("## 新增公告 / New Announcement")
        st.caption(
            "管理員只需輸入中文；發布時系統會自動產生英文翻譯。"
        )

        title = st.text_input(
            "中文公告標題",
            key="announcement_title_zh",
        )
        content = st.text_area(
            "中文公告內容",
            key="announcement_content_zh",
        )

        a, b = st.columns(2)
        with a:
            sd = st.date_input(
                "公告開始",
                value=date.today(),
                key="ann_sd",
            )
        with b:
            ed = st.date_input(
                "公告結束",
                value=date.today() + timedelta(days=30),
                key="ann_ed",
            )

        if st.button(
            "自動翻譯並發布公告",
            key="announcement_publish_button",
        ):
            if not title.strip() or not content.strip():
                st.error("請輸入中文公告標題與內容。")
            elif sd > ed:
                st.error("公告開始日期不可晚於結束日期。")
            else:
                try:
                    with st.spinner("正在產生英文翻譯…"):
                        title_en = translate_zh_to_en(title.strip())
                        content_en = translate_zh_to_en(content.strip())

                    if not title_en or not content_en:
                        st.error("英文翻譯未完成，請稍後再試。")
                    else:
                        save_announcement(
                            title.strip(),
                            content.strip(),
                            title_en,
                            content_en,
                            str(sd),
                            str(ed),
                            True,
                        )
                        st.success("中英文公告已自動產生並發布。")
                        st.rerun()
                except Exception as exc:
                    st.error(
                        "自動翻譯失敗，公告尚未發布。"
                        "請確認 Streamlit Cloud 可以連線至翻譯服務後再試。"
                    )
                    st.caption(str(exc))

        items = get_announcements()
        if items:
            st.dataframe(
                pd.DataFrame(items),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("### 編輯雙語公告 / Edit Bilingual Announcement")

            edit_options = {
                (
                    f'#{item["id"]}｜{item["title"]}｜'
                    f'{item["start_date"]}～{item["end_date"]}'
                ): item
                for item in items
            }
            edit_label = st.selectbox(
                "選擇要編輯的公告",
                list(edit_options.keys()),
                key="announcement_edit_select",
            )
            edit_item = edit_options[edit_label]

            edit_title = st.text_input(
                "編輯中文標題",
                value=str(edit_item.get("title") or ""),
                key=f'announcement_edit_title_{edit_item["id"]}',
            )
            edit_content = st.text_area(
                "編輯中文內容",
                value=str(edit_item.get("content") or ""),
                key=f'announcement_edit_content_{edit_item["id"]}',
            )
            current_title_en = str(edit_item.get("title_en") or "")
            current_content_en = str(edit_item.get("content_en") or "")

            with st.expander("目前英文翻譯 / Current English Translation"):
                st.markdown(f"**{current_title_en or '—'}**")
                st.write(current_content_en or "—")

            edit_col1, edit_col2 = st.columns(2)
            with edit_col1:
                edit_start = st.date_input(
                    "編輯公告開始",
                    value=edit_item["start_date"],
                    key=f'announcement_edit_start_{edit_item["id"]}',
                )
            with edit_col2:
                edit_end = st.date_input(
                    "編輯公告結束",
                    value=edit_item["end_date"],
                    key=f'announcement_edit_end_{edit_item["id"]}',
                )

            edit_active = st.checkbox(
                "公告啟用",
                value=bool(edit_item.get("is_active")),
                key=f'announcement_edit_active_{edit_item["id"]}',
            )

            if st.button(
                "重新翻譯並儲存公告修改",
                key="announcement_edit_save",
            ):
                if not edit_title.strip() or not edit_content.strip():
                    st.error("請輸入中文公告標題與內容。")
                elif edit_start > edit_end:
                    st.error("公告開始日期不可晚於結束日期。")
                else:
                    try:
                        with st.spinner("正在重新產生英文翻譯…"):
                            edit_title_en = translate_zh_to_en(
                                edit_title.strip()
                            )
                            edit_content_en = translate_zh_to_en(
                                edit_content.strip()
                            )

                        updated = update_announcement_bilingual(
                            edit_item["id"],
                            edit_title.strip(),
                            edit_content.strip(),
                            edit_title_en,
                            edit_content_en,
                            str(edit_start),
                            str(edit_end),
                            edit_active,
                        )
                        if updated:
                            st.success("公告及英文翻譯已更新。")
                            st.rerun()
                        else:
                            st.warning("找不到指定公告。")
                    except Exception as exc:
                        st.error(
                            "自動翻譯失敗，公告修改尚未儲存。"
                        )
                        st.caption(str(exc))

            st.markdown("### 刪除既有公告")
            announcement_options = {
                (
                    f'#{item["id"]}｜{item["title"]}｜'
                    f'{item["start_date"]}～{item["end_date"]}'
                ): item["id"]
                for item in items
            }
            selected_label = st.selectbox(
                "選擇要刪除的公告",
                list(announcement_options.keys()),
                key="announcement_delete_select",
            )
            confirm_delete = st.checkbox(
                "我確認要永久刪除此公告",
                key="announcement_delete_confirm",
            )
            if st.button(
                "刪除公告",
                key="announcement_delete_button",
            ):
                if not confirm_delete:
                    st.error("請先勾選確認。")
                else:
                    deleted = delete_announcement(
                        announcement_options[selected_label]
                    )
                    if deleted:
                        st.success("公告已刪除。")
                        st.rerun()
                    else:
                        st.warning("找不到指定公告，可能已被刪除。")
        else:
            st.info("目前尚無公告紀錄。")
    with tabs[9]:
        day=st.date_input("停借日期",value=date.today(),key="closure_day")
        room=st.selectbox("適用教室",["全部教室"]+[r["room_name"] for r in get_classrooms()])
        reason=st.text_input("停借原因")
        if st.button("新增停借"):
            if not reason.strip():
                st.error("請輸入停借原因。")
            else:
                save_closure(
                    str(day),
                    "" if room == "全部教室" else room,
                    reason.strip(),
                )
                st.rerun()
        items=get_closures()
        if items: st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
    with tabs[10]:
        approval=st.radio("借用審核模式",["manual","auto"],index=0 if get_setting("approval_mode","manual")=="manual" else 1,horizontal=True,format_func=lambda x:"人工審核" if x=="manual" else "自動核准")
        max_days=st.number_input("最多可預約未來天數",min_value=1,max_value=365,value=int(get_setting("max_days_ahead","180")))
        if st.button("儲存系統設定"):
            set_setting("approval_mode",approval); set_setting("max_days_ahead",str(max_days)); st.success("已儲存")
        st.caption("Email 通知需在 Streamlit Secrets 設定 [smtp]。")
    with tabs[11]:
        logs=get_audit_logs()
        if logs:
            st.dataframe(pd.DataFrame(logs),use_container_width=True,hide_index=True)
            st.download_button(
                "匯出操作紀錄",
                excel_bytes(logs, "操作紀錄"),
                f"audit_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


st.set_page_config(page_title="AU-PCRS V7.0.2",layout="wide")
apply_style()
for key,default in {"language":"中文","user":None,"admin":False}.items():
    if key not in st.session_state: st.session_state[key]=default
try: init_db()
except Exception as exc:
    st.error("Database initialization failed / 資料庫初始化失敗"); st.caption(str(exc)); st.stop()

language=st.sidebar.selectbox("語言 / Language",["中文","English"],index=0 if st.session_state.language=="中文" else 1)
st.session_state.language=language
t=TEXT[language]
header(t)

if st.session_state.user is None:
    login(t); footer(); st.stop()

with st.sidebar:
    st.markdown(f'### {st.session_state.user["name"]}')
    if st.button(t["logout"],use_container_width=True):
        u=st.session_state.user
        record_logout(u["user_type"],u["identification_code"],u["name"])
        st.session_state.user=None; st.session_state.admin=False; st.rerun()

page=st.sidebar.radio("Menu / 選單",
    [t["home"], t["admin_panel"], t["tv_mode"]]
    if st.session_state.admin
    else [
        t["home"],
        t["my_bookings"],
        t["reserve"],
        t["calendar"],
        t["weekly"],
        t["ai_assistant"],
        t["tv_mode"],
    ]
)

if page==t["home"]: home(t)
elif page==t["my_bookings"]: my_bookings(t)
elif page==t["reserve"]: reserve(t)
elif page==t["calendar"]: calendar_view(t)
elif page==t["weekly"]: weekly_schedule_view(t, "user_weekly")
elif page==t["ai_assistant"]: ai_assistant_page(t)
elif page==t["tv_mode"]: tv_mode_page()
else: admin_panel()
footer()
