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
    get_setting, get_user_bookings, get_room_statuses, get_booking_statistics, get_week_schedule, import_authorized_users, init_db,
    record_login, record_logout, review_booking, save_announcement,
    save_classroom, save_closure, save_open_period, set_course_semester_active,
    set_setting, verify_authorized_user_by_code,
)
from notifications import send_booking_email
from reports import booking_pdf, booking_qr_png

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
        "reserve":"我要借教室","calendar":"教室行事曆","weekly":"視覺化週課表","admin_panel":"管理員後台",
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
        "reserve":"Reserve a Classroom","calendar":"Classroom Calendar","weekly":"Weekly Schedule","admin_panel":"Admin Panel",
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
        st.markdown(f'<div class="hero"><div class="h1">{t["title1"]}</div><div class="h2">{t["title2"]}</div><div class="sub">{t["subtitle"]}</div><div class="pill">AU-PCRS V5.0 Enterprise</div></div>', unsafe_allow_html=True)
    with right:
        if AU_LOGO.exists(): st.image(str(AU_LOGO), width=170)


def footer():
    st.markdown('<div class="footer">Asia University Department of Psychology<br>© 2026 AU-PCRS Enterprise</div>', unsafe_allow_html=True)


def login(t):
    st.markdown(f'<div class="login-card"><h2>{t["login_title"]} / System Login</h2></div>', unsafe_allow_html=True)
    roles = [t["faculty"], t["student"], t["admin"]]
    with st.form("login"):
        role = st.radio("身分 / Role", roles, horizontal=True)
        credential = st.text_input(t["admin_password"] if role==t["admin"] else t["id_code"], type="password" if role==t["admin"] else "default")
        submitted = st.form_submit_button(t["login"], use_container_width=True)
    if submitted:
        if role == t["admin"]:
            if credential == admin_password():
                st.session_state.user={"user_type":"管理員","name":"Administrator","identification_code":"ADMIN","email":""}
                st.session_state.admin=True
                record_login("管理員","ADMIN","Administrator",True)
                st.rerun()
            st.error(t["invalid_admin"])
        else:
            kind = "教師" if role==t["faculty"] else "學生"
            user = verify_authorized_user_by_code(kind, credential)
            if user:
                st.session_state.user=user; st.session_state.admin=False
                record_login(user["user_type"],user["identification_code"],user["name"],True)
                st.rerun()
            st.error(t["invalid_user"])
    st.caption(t["privacy"])


def announcements_block():
    items = get_announcements(active_only=True)
    if items:
        st.markdown("### 最新公告 / Announcements")
        for item in items:
            st.markdown(f'<div class="announcement"><b>{item["title"]}</b><br>{item["content"]}</div>', unsafe_allow_html=True)



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


def analytics_dashboard():
    st.markdown("### 使用統計 / Usage Analytics")
    period_days = st.selectbox(
        "統計期間",
        [7, 30, 90, 180, 365],
        index=1,
        format_func=lambda value: f"最近 {value} 天",
        key="analytics_days",
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


def weekly_schedule_view(t):
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
            key="week_start",
        )
    with right:
        selected_room = st.selectbox(
            t["room"],
            room_options,
            key="week_room",
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
    analytics_dashboard()


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
        analytics_dashboard()
        weekly_schedule_view(TEXT[st.session_state.language])
    with tabs[2]:
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
    with tabs[3]:
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
    with tabs[4]:
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
    with tabs[5]:
        semester=st.text_input("匯入學期",value="115-1",key="course_sem")
        replace=st.checkbox("清除此學期既有課表")
        upload=st.file_uploader("課表 Excel",type=["xlsx"],key="course_file")
        if upload is not None:
            frame=pd.read_excel(upload,dtype=str).fillna(""); st.dataframe(frame.head(30),use_container_width=True,hide_index=True)
            if st.button("匯入課表"): st.success(add_course_blocks(frame,semester,replace)); st.rerun()
        semesters=get_course_semesters()
        if semesters: st.dataframe(pd.DataFrame(semesters),use_container_width=True,hide_index=True)
    with tabs[6]:
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
            if st.button("儲存審核結果"):
                review_booking(selected,new_status,"Administrator",note)
                item=get_booking_by_id(selected)
                email_ok, email_message = send_booking_email(
                    item["email"],
                    "AU-PCRS Review",
                    f"Reservation {selected}: {new_status}\n{note}",
                )
                if not email_ok and email_message != "SMTP secrets not configured":
                    st.warning(f"審核結果已儲存，但 Email 寄送失敗：{email_message}")
                st.rerun()
        else: st.info("查無借用紀錄")
    with tabs[7]:
        title=st.text_input("公告標題")
        content=st.text_area("公告內容")
        a,b=st.columns(2)
        with a: sd=st.date_input("公告開始",value=date.today(),key="ann_sd")
        with b: ed=st.date_input("公告結束",value=date.today()+timedelta(days=30),key="ann_ed")
        if st.button("發布公告"):
            if not title.strip() or not content.strip():
                st.error("請輸入公告標題與內容。")
            elif sd > ed:
                st.error("公告開始日期不可晚於結束日期。")
            else:
                save_announcement(
                    title.strip(), content.strip(), str(sd), str(ed), True
                )
                st.rerun()
        items=get_announcements()
        if items: st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
    with tabs[8]:
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
    with tabs[9]:
        approval=st.radio("借用審核模式",["manual","auto"],index=0 if get_setting("approval_mode","manual")=="manual" else 1,horizontal=True,format_func=lambda x:"人工審核" if x=="manual" else "自動核准")
        max_days=st.number_input("最多可預約未來天數",min_value=1,max_value=365,value=int(get_setting("max_days_ahead","180")))
        if st.button("儲存系統設定"):
            set_setting("approval_mode",approval); set_setting("max_days_ahead",str(max_days)); st.success("已儲存")
        st.caption("Email 通知需在 Streamlit Secrets 設定 [smtp]。")
    with tabs[10]:
        logs=get_audit_logs()
        if logs:
            st.dataframe(pd.DataFrame(logs),use_container_width=True,hide_index=True)
            st.download_button(
                "匯出操作紀錄",
                excel_bytes(logs, "操作紀錄"),
                f"audit_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


st.set_page_config(page_title="AU-PCRS V5.0",layout="wide")
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
    [t["home"],t["admin_panel"]] if st.session_state.admin
    else [
        t["home"],
        t["my_bookings"],
        t["reserve"],
        t["calendar"],
        t["weekly"],
    ]
)

if page==t["home"]: home(t)
elif page==t["my_bookings"]: my_bookings(t)
elif page==t["reserve"]: reserve(t)
elif page==t["calendar"]: calendar_view(t)
elif page==t["weekly"]: weekly_schedule_view(t)
else: admin_panel()
footer()
