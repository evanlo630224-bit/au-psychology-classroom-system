import base64
import io
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from database import *

BASE_DIR = Path(__file__).parent
PSY_LOGO = BASE_DIR / "assets" / "psychology_logo.jpg"
AU_LOGO = BASE_DIR / "assets" / "asia_university_logo.png"
ROOMS = ["M502", "M506", "M507", "M510", "800A"]
SLOTS = [
    ("08:10", "09:00"), ("09:10", "10:00"), ("10:10", "11:00"),
    ("11:10", "12:00"), ("12:10", "13:00"), ("13:10", "14:00"),
    ("14:10", "15:00"), ("15:10", "16:00"), ("16:10", "17:00"),
    ("17:10", "18:00"), ("18:25", "19:10"), ("19:10", "19:55"),
    ("20:00", "20:45"), ("20:50", "21:35"), ("21:35", "22:20"),
]
TXT = {
    "中文": {
        "faculty": "教師", "student": "學生", "admin": "管理員",
        "home": "首頁", "reserve": "我要借教室", "query": "教室查詢",
        "adminp": "管理員後台", "logout": "登出",
    },
    "English": {
        "faculty": "Faculty", "student": "Student", "admin": "Administrator",
        "home": "Home", "reserve": "Reserve a Classroom", "query": "Check Availability",
        "adminp": "Admin Panel", "logout": "Log Out",
    },
}

SVG = {
    "calendar": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2v3M17 2v3M3.5 9h17M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 13h3M14 13h3M7 17h3M14 17h3"/></svg>',
    "search": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4.2-4.2"/></svg>',
    "settings": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3v-4h.1A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.1A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.2.36.6.73 1 .9.3.13.66.2 1.1.2h.1v4h-.1c-.44 0-.8.07-1.1.2-.4.17-.8.54-1 .9Z"/></svg>',
    "notice": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11v2a2 2 0 0 0 2 2h2l3 4h2l-1.5-4H14l6 3V6l-6 3H6a2 2 0 0 0-2 2Z"/></svg>',
    "book": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5v-16ZM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5A2.5 2.5 0 0 1 20 21.5v-16Z"/></svg>',
    "news": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14a2 2 0 0 1 2 2v13H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 8h7M7 12h10M7 16h10"/></svg>',
}


def admin_password():
    try:
        if "ADMIN_PASSWORD" in st.secrets:
            return str(st.secrets["ADMIN_PASSWORD"])
        if "admin" in st.secrets and "password" in st.secrets["admin"]:
            return str(st.secrets["admin"]["password"])
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "admin123")


def valid_email(value):
    return re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", value.strip()) is not None


def valid_phone(value):
    return len(re.sub(r"\D", "", value)) >= 8


def xlsx(rows, sheet="資料"):
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, sheet_name=sheet, engine="openpyxl")
    return buffer.getvalue()


def image_data_uri(path: Path):
    if not path.exists():
        return ""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def feature(icon, title, subtitle):
    return f'<div class="feature"><div class="icon">{SVG[icon]}</div><div><b>{title}</b><span>{subtitle}</span></div></div>'


def quick(icon, title, subtitle):
    return f'<div class="quick"><div class="quick-icon">{SVG[icon]}</div><div><b>{title}</b><p>{subtitle}</p></div><span class="arrow">›</span></div>'


def style(login_mode=False):
    login_css = """
    [data-testid="stSidebar"], [data-testid="collapsedControl"]{display:none!important}
    .block-container{padding-left:2.1rem!important;padding-right:2.1rem!important}
    """ if login_mode else ""
    st.markdown(f'''<style>
    :root{{--p:#35148f;--v:#5d32dc;--v2:#7446eb;--l:#f5f2ff;--b:#e5def8;--i:#252536;--m:#747287}}
    html,body,[class*=css]{{font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif}}
    .stApp{{background:radial-gradient(circle at 4% 82%,rgba(90,48,220,.075),transparent 23%),radial-gradient(circle at 96% 8%,rgba(90,48,220,.095),transparent 26%),linear-gradient(180deg,#fcfbff,#fff 72%)}}
    header[data-testid=stHeader]{{background:transparent;height:0}}
    #MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],.stAppDeployButton{{display:none!important;visibility:hidden!important}}
    .block-container{{max-width:1430px;padding-top:1.25rem;padding-bottom:.9rem}}
    [data-testid=stSidebar]{{background:linear-gradient(180deg,#28106f 0%,#4720bd 54%,#6638df 100%);border-right:0}}
    [data-testid=stSidebar] h1,
    [data-testid=stSidebar] h2,
    [data-testid=stSidebar] h3,
    [data-testid=stSidebar] label[data-testid="stWidgetLabel"] p,
    [data-testid=stSidebar] [data-testid="stCaptionContainer"],
    [data-testid=stSidebar] hr{{color:white!important}}
    [data-testid=stSidebar] [data-testid="stImage"] img{{
        border-radius:20px!important;
        background:rgba(255,255,255,.96)!important;
        padding:7px!important;
        box-shadow:0 12px 30px rgba(20,7,70,.24)!important;
    }}
    [data-testid=stSidebar] [data-baseweb="select"]>div{{
        background:#fff!important;
        border:1px solid rgba(255,255,255,.58)!important;
        border-radius:12px!important;
        min-height:48px!important;
    }}
    [data-testid=stSidebar] [data-baseweb="select"] span,
    [data-testid=stSidebar] [data-baseweb="select"] input,
    [data-testid=stSidebar] [data-baseweb="select"] svg{{
        color:#2f176e!important;
        -webkit-text-fill-color:#2f176e!important;
        fill:#2f176e!important;
        font-weight:800!important;
    }}
    [data-testid=stSidebar] div[role="radiogroup"]{{
        display:flex!important;
        flex-direction:column!important;
        gap:9px!important;
    }}
    [data-testid=stSidebar] div[role="radiogroup"] label{{
        width:100%!important;
        min-height:48px!important;
        display:flex!important;
        align-items:center!important;
        background:rgba(255,255,255,.97)!important;
        border:1px solid rgba(255,255,255,.65)!important;
        border-radius:13px!important;
        padding:10px 13px!important;
        margin:0!important;
        box-shadow:0 6px 18px rgba(25,8,82,.10)!important;
    }}
    [data-testid=stSidebar] div[role="radiogroup"] label p,
    [data-testid=stSidebar] div[role="radiogroup"] label span{{
        color:#2e176c!important;
        -webkit-text-fill-color:#2e176c!important;
        font-weight:800!important;
        opacity:1!important;
    }}
    [data-testid=stSidebar] div[role="radiogroup"] label:has(input:checked),
    [data-testid=stSidebar] div[role="radiogroup"] label[data-checked="true"]{{
        background:linear-gradient(100deg,#efe9ff,#ffffff)!important;
        border:2px solid #bba8ff!important;
        box-shadow:0 8px 22px rgba(66,31,168,.18)!important;
    }}
    [data-testid=stSidebar] div[role="radiogroup"] label:has(input:checked) p,
    [data-testid=stSidebar] div[role="radiogroup"] label:has(input:checked) span{{
        color:#4c22bd!important;
        -webkit-text-fill-color:#4c22bd!important;
    }}
    [data-testid=stSidebar] div[role="radiogroup"] input[type="radio"]{{
        accent-color:#6337dc!important;
    }}
    [data-testid=stSidebar] .stButton>button{{
        background:rgba(255,255,255,.97)!important;
        color:#3a1a91!important;
        border:1px solid rgba(255,255,255,.65)!important;
        min-height:46px!important;
        box-shadow:0 7px 18px rgba(24,7,77,.12)!important;
    }}
    [data-baseweb="popover"] *{{color:#252536!important}}
    .topbar{{display:flex;justify-content:space-between;align-items:center;padding:12px 20px;border-radius:17px;background:linear-gradient(110deg,#2e117f,#6033da);color:#fff;box-shadow:0 12px 32px rgba(55,25,145,.17);margin-bottom:18px}}
    .brand{{font-weight:850;font-size:1.02rem}}.brand span{{display:block;font-size:.72rem;font-weight:500;opacity:.82;margin-top:2px}}
    .language-row{{display:flex;align-items:center;gap:12px}}.lang-caption{{font-size:.74rem;opacity:.8}}
    .hero{{padding:8px 8px 0}}
    .logo-wrap{{height:132px;display:flex;align-items:center;margin-bottom:3px}}
    .brand-logo{{width:138px;max-height:128px;object-fit:contain;mix-blend-mode:multiply;filter:contrast(1.04)}}
    .logo-fallback{{width:104px;height:104px;border-radius:28px;background:linear-gradient(140deg,#4b21c5,#7849ed);display:flex;align-items:center;justify-content:center;color:#fff;font:800 3rem Georgia,serif;box-shadow:0 14px 34px rgba(69,31,175,.18)}}
    .eyebrow{{color:var(--v);font-weight:850;letter-spacing:.13em;font-size:.72rem}}
    .t1{{font-size:clamp(2rem,3.45vw,3.32rem);font-weight:900;color:var(--p);line-height:1.12;margin:10px 0 7px}}
    .t2{{font-size:clamp(1.42rem,2.25vw,2.2rem);font-weight:850;color:var(--i);line-height:1.25}}
    .sub{{font-size:1rem;color:#6e6b80;margin-top:12px}}
    .desc{{font-size:.96rem;color:#464456;line-height:1.75;margin:19px 0 15px;max-width:720px}}
    .features{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
    .feature{{display:flex;align-items:center;gap:11px;background:rgba(255,255,255,.94);border:1px solid var(--b);border-radius:15px;padding:12px 13px;box-shadow:0 8px 20px rgba(67,34,160,.055)}}
    .feature .icon,.quick-icon{{width:35px;height:35px;min-width:35px;border-radius:11px;background:#f0ebff;display:flex;align-items:center;justify-content:center;color:var(--v)}}
    .feature svg,.quick svg{{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}}
    .feature b{{display:block;margin-bottom:2px;color:#302c3e;font-size:.91rem}}.feature span,.quick p{{font-size:.72rem;color:var(--m);margin:0}}
    div[data-testid="stVerticalBlockBorderWrapper"]{{border:1px solid var(--b)!important;border-radius:25px!important;background:rgba(255,255,255,.97)!important;box-shadow:0 22px 54px rgba(55,25,145,.13)!important;padding:0!important}}
    div[data-testid="stVerticalBlockBorderWrapper"]>div{{padding:24px 27px 19px!important}}
    .login-title{{font-size:1.82rem;font-weight:900;color:var(--p);margin-bottom:2px}}.login-caption{{font-size:.82rem;color:var(--m)}}
    .rule{{width:42px;height:3px;border-radius:99px;background:linear-gradient(90deg,#7547ed,#3d1aa6);margin:9px 0 13px}}
    div[role=radiogroup]{{gap:0!important}}
    div[role=radiogroup] label{{border:1px solid #ded8f2;padding:.38rem .82rem;border-radius:10px;background:#fff;margin-right:4px}}
    .stTextInput input,.stTextArea textarea,.stDateInput input{{border-radius:11px!important;border:1px solid #ddd7ef!important;background:#fcfbff!important}}
    .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{{border-radius:11px!important;font-weight:800!important}}
    .stFormSubmitButton>button{{min-height:2.75rem;background:linear-gradient(100deg,#6736dd,#3d19ad)!important;color:#fff!important;border:0!important;box-shadow:0 9px 22px rgba(76,37,190,.2)}}
    div[data-testid=stMetric]{{border:1px solid var(--b);border-radius:18px;padding:15px;background:#fff;box-shadow:0 10px 24px rgba(66,34,157,.07)}}
    .login-links{{display:flex;justify-content:space-around;color:#777287;font-size:.75rem;padding-top:1px}}
    .privacy{{color:#8b8697;font-size:.72rem;text-align:center;margin-top:11px}}
    .quick-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px}}
    .quick{{position:relative;display:flex;align-items:center;gap:12px;background:#fff;border:1px solid var(--b);border-radius:16px;padding:13px 15px;box-shadow:0 7px 20px rgba(67,34,160,.05)}}
    .quick b{{font-size:.92rem;color:#302c3e}}.quick .arrow{{position:absolute;right:14px;color:#77718b;font-size:1.45rem}}
    .footer-note{{text-align:center;color:#827e92;font-size:.72rem;margin-top:14px}}
    @media(max-width:900px){{.features,.quick-grid{{grid-template-columns:1fr}}.logo-wrap{{height:auto}}.block-container{{padding-left:1rem!important;padding-right:1rem!important}}}}
    {login_css}
    </style>''', unsafe_allow_html=True)


def topbar(language_selector=False):
    c1, c2 = st.columns([5.4, 1.15], vertical_alignment="center")
    with c1:
        st.markdown('''<div class="topbar" style="margin-bottom:0"><div class="brand">亞洲大學心理學系<span>Department of Psychology, Asia University</span></div><div class="language-row"><span class="lang-caption">AU-PCRS</span></div></div>''', unsafe_allow_html=True)
    with c2:
        if language_selector:
            language = st.selectbox("語言 / Language", ["中文", "English"], index=0 if st.session_state.language == "中文" else 1, label_visibility="collapsed")
            if language != st.session_state.language:
                st.session_state.language = language
                st.rerun()
        else:
            st.markdown('<div style="height:47px;display:flex;align-items:center;justify-content:center;border:1px solid #e5def8;border-radius:14px;background:#fff;color:#3c1aa5;font-weight:800">中文 / English</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)


def login_page():
    topbar(language_selector=True)
    left, right = st.columns([1.2, .86], gap="large", vertical_alignment="top")
    with left:
        logo_uri = image_data_uri(PSY_LOGO)
        if logo_uri:
            logo_html = f'<div class="logo-wrap"><img class="brand-logo" src="{logo_uri}" alt="Department of Psychology logo"></div>'
        else:
            logo_html = '<div class="logo-wrap"><div class="logo-fallback">Ψ</div></div>'
        st.markdown(
            logo_html + '''<div class="hero"><div class="eyebrow">AU-PCRS · PROFESSIONAL ADMINISTRATIVE PORTAL</div><div class="t1">亞洲大學心理學系</div><div class="t2">專業教室借用及查詢系統</div><div class="sub">AU Psychology Classroom Reservation System</div><div class="desc">提供教師、學生與管理者進行教室借用、查詢與行政管理之整合平台。</div><div class="features">'''
            + feature("calendar", "教室借用", "線上申請與衝堂檢核")
            + feature("search", "借用查詢", "即時查看教室使用狀態")
            + feature("settings", "行政管理", "名冊、課表與借用管理")
            + '</div></div>',
            unsafe_allow_html=True,
        )
    with right:
        with st.container(border=True):
            st.markdown('<div class="login-title">系統登入 / System Login</div><div class="login-caption">請選擇身分並輸入登入資料</div><div class="rule"></div>', unsafe_allow_html=True)
            with st.form("login", clear_on_submit=False):
                role = st.radio("身分 / Role", ["教師", "學生", "管理員"], horizontal=True)
                is_admin = role == "管理員"
                cred = st.text_input(
                    "管理員密碼" if is_admin else "教師職編／學生學號",
                    type="password" if is_admin else "default",
                    placeholder="請輸入管理員密碼" if is_admin else "請輸入教師職編或學生學號",
                )
                st.checkbox("記住我的帳號 / Remember me")
                submitted = st.form_submit_button("登入 Login", use_container_width=True)
            st.markdown('<div class="login-links"><span>🔒 忘記密碼？</span><span>☎ 聯絡系辦</span></div>', unsafe_allow_html=True)
            if submitted:
                if not cred.strip():
                    st.error("請輸入登入資料。")
                elif is_admin:
                    if cred == admin_password():
                        st.session_state.user = {"user_type": "管理員", "name": "Administrator", "identification_code": "ADMIN", "email": ""}
                        st.session_state.admin = True
                        st.rerun()
                    else:
                        st.error("管理員密碼錯誤。")
                else:
                    user = verify_authorized_user_by_code(role, cred)
                    if user:
                        st.session_state.user = user
                        st.session_state.admin = False
                        st.rerun()
                    else:
                        st.error("身分驗證失敗，僅限心理學系教師及學生使用。")
            st.markdown('<div class="privacy">本系統僅供亞洲大學心理學系教師與學生使用。</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="quick-grid">'
        + quick("calendar", "教室課表", "查看課表與使用狀況")
        + quick("notice", "系統公告", "重要通知與公告")
        + quick("book", "使用說明", "操作手冊與指南")
        + quick("news", "最新消息", "系統更新資訊")
        + '</div><div class="footer-note">AU-PCRS V8.5 Database Migration Fix Edition ｜ © 2026 亞洲大學心理學系</div>',
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    """Render the dashboard directly. Do not wrap this call in st.write()."""
    st.markdown("## 智慧儀表板 / Dashboard")
    counts = get_dashboard_counts()
    a, b, c, d = st.columns(4)
    a.metric("教師 Faculty", counts["teachers"])
    b.metric("學生 Students", counts["students"])
    c.metric("有效借用 Active", counts["active_bookings"])
    d.metric("專業教室 Rooms", len(ROOMS))
    period = get_active_open_period()
    if period:
        st.success(f"目前開放：{period['semester']}｜{period['start_date']}～{period['end_date']}")
    else:
        st.warning("尚未設定開放借用期間")
    ok, message = database_health_check()
    if ok:
        st.info(f"✅ Database：{message}")
    else:
        st.error(f"❌ Database：{message}")


def reserve():
    user = st.session_state.user
    st.markdown("## 我要借教室 / Reserve")
    st.info(f"登入者：{user['name']}（{user['user_type']}）")
    with st.form("booking"):
        left, right = st.columns(2)
        with left:
            booking_date = st.date_input("借用日期", value=date.today(), min_value=date.today())
            room = st.selectbox("教室", ROOMS)
            start = st.selectbox("開始時間", [x for x, _ in SLOTS])
            end = st.selectbox("結束時間", [x for _, x in SLOTS])
        with right:
            phone = st.text_input("聯絡手機")
            email = st.text_input("聯絡信箱", value=user.get("email") or "")
            reason = st.text_area("借用事由", height=160)
        submitted = st.form_submit_button("送出申請", use_container_width=True)
    if submitted:
        if not phone.strip() or not email.strip() or not reason.strip():
            st.error("請完整填寫必填欄位。")
            return
        if not valid_phone(phone) or not valid_email(email) or start >= end:
            st.error("輸入格式不正確。")
            return
        period = get_active_open_period()
        if not period or not (str(period["start_date"]) <= str(booking_date) <= str(period["end_date"])):
            st.error("所選日期不在開放期間。")
            return
        conflict = check_booking_conflict(str(booking_date), room, start, end)
        if conflict:
            st.error(f"時段衝突：{conflict['detail']}")
            return
        booking_id = create_booking(str(booking_date), room, start, end, user["user_type"], user["name"], user["identification_code"], phone, email, reason)
        st.success(f"申請完成，借用編號：{booking_id}")


def query():
    st.markdown("## 教室查詢 / Availability")
    left, right = st.columns(2)
    with left:
        query_date = st.date_input("日期", value=date.today(), key="qd")
    with right:
        query_room = st.selectbox("教室", ROOMS, key="qr")
    courses = get_course_blocks(str(query_date), query_room)
    bookings = [x for x in get_all_bookings() if str(x["booking_date"]) == str(query_date) and x["room"] == query_room and x["status"] == "有效"]
    output = []
    for start, end in SLOTS:
        status, detail = "可借用", ""
        for course in courses:
            if start < str(course["end_time"])[:5] and end > str(course["start_time"])[:5]:
                status, detail = "已排課", course["course_name"]
                break
        if status == "可借用":
            for booking in bookings:
                if start < str(booking["end_time"])[:5] and end > str(booking["start_time"])[:5]:
                    status, detail = "已借用", booking["reason"]
                    break
        output.append({"時間": f"{start}–{end}", "狀態": status, "說明": detail})
    st.dataframe(pd.DataFrame(output), use_container_width=True, hide_index=True)


def admin_page():
    st.markdown("## 管理員後台")
    tabs = st.tabs(["儀表板", "名冊管理", "開放期間", "課表管理", "借用管理", "操作紀錄"])
    with tabs[0]:
        _ = render_dashboard()
    with tabs[1]:
        user_type = st.radio("名冊類別", ["教師", "學生"], horizontal=True)
        upload = st.file_uploader("Excel：辨識碼、姓名、聯絡信箱、狀態", type=["xlsx"], key="roster")
        replace = st.checkbox("覆蓋此類名冊")
        if st.button("匯入名冊", use_container_width=True):
            if upload is None:
                st.error("請先選擇檔案")
            else:
                try:
                    st.success(import_authorized_users(pd.read_excel(upload, dtype=str).fillna(""), user_type, replace))
                except Exception as exc:
                    st.error(exc)
        rows = get_all_authorized_users()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with tabs[2]:
        left, right = st.columns(2)
        with left:
            start_date = st.date_input("開始日期", value=date.today())
        with right:
            end_date = st.date_input("結束日期", value=date.today())
        semester = st.text_input("學期", value="115-1")
        if st.button("儲存並啟用", use_container_width=True):
            if start_date > end_date:
                st.error("結束日期不得早於開始日期。")
            else:
                save_open_period(semester, str(start_date), str(end_date))
                st.success("已儲存")
    with tabs[3]:
        semester = st.text_input("匯入學期", value="115-1", key="sem")
        replace = st.checkbox("清除此學期既有課表")
        upload = st.file_uploader("課表 Excel", type=["xlsx"], key="course")
        if upload is not None:
            frame = pd.read_excel(upload, dtype=str).fillna("")
            st.dataframe(frame.head(20), use_container_width=True, hide_index=True)
            if st.button("確認匯入課表", use_container_width=True):
                st.success(add_course_blocks(frame, semester, replace))
        semesters = get_course_semesters()
        if semesters:
            st.dataframe(pd.DataFrame(semesters), use_container_width=True, hide_index=True)
    with tabs[4]:
        rows = get_all_bookings()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.download_button("匯出 Excel", xlsx(rows, "借用紀錄"), f"bookings_{date.today()}.xlsx", use_container_width=True)
            booking_id = st.selectbox("借用編號", [r["booking_id"] for r in rows])
            reason = st.text_input("取消原因")
            if st.button("取消借用") and reason.strip():
                cancel_booking(booking_id, reason.strip())
                st.rerun()
        else:
            st.info("目前尚無借用紀錄")
    with tabs[5]:
        logs = get_audit_logs()
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無操作紀錄")


st.set_page_config(page_title="AU-PCRS V8.5", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
for key, value in {"language": "中文", "user": None, "admin": False}.items():
    if key not in st.session_state:
        st.session_state[key] = value

try:
    init_db()
except Exception as exc:
    style(login_mode=True)
    st.error("資料庫初始化失敗")
    st.caption(str(exc))
    st.stop()

if st.session_state.user is None:
    style(login_mode=True)
    _ = login_page()
    st.stop()

style(login_mode=False)
with st.sidebar:
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if PSY_LOGO.exists():
        st.image(str(PSY_LOGO), width=92)
    st.markdown(f"### {st.session_state.user['name']}")
    st.caption(f"身分 / Role：{st.session_state.user['user_type']}")
    st.divider()

    selected_language = st.selectbox(
        "語言 / Language",
        ["中文", "English"],
        index=0 if st.session_state.language == "中文" else 1,
        key="sidebar_language",
    )
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        st.rerun()

    t = TXT[st.session_state.language]
    if st.session_state.admin:
        pages = [t["home"], t["adminp"]]
    else:
        pages = [t["home"], t["reserve"], t["query"]]

    page = st.radio(
        "功能選單 / Menu",
        pages,
        key="sidebar_page",
    )

    st.divider()
    st.caption("AU-PCRS V8.5")
    st.caption("Database Migration Fix Edition")
    if st.button(t["logout"], use_container_width=True, key="sidebar_logout"):
        st.session_state.user = None
        st.session_state.admin = False
        st.rerun()

topbar(language_selector=False)
if page == t["home"]:
    _ = render_dashboard()
elif page == t["reserve"]:
    _ = reserve()
elif page == t["query"]:
    _ = query()
else:
    _ = admin_page()
