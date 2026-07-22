import base64
import io
import os
import re
from datetime import date, datetime, timedelta
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

PORTAL_TEXT = {
    "中文": {
        "dept":"亞洲大學心理學系","system":"專業教室借用及查詢系統","subtitle":"AU Psychology Classroom Reservation System",
        "description":"提供教師、學生與管理者進行教室借用、查詢與行政管理之整合平台。",
        "reserve_title":"教室借用","reserve_sub":"線上申請與衝堂檢核","query_title":"借用查詢","query_sub":"即時查看教室使用狀態",
        "admin_title":"行政管理","admin_sub":"名冊、課表與借用管理","login_title":"系統登入","login_caption":"請選擇身分並輸入登入資料",
        "role":"身分 / Role","faculty":"教師","student":"學生","admin":"管理員","account_label":"教師職編／學生學號",
        "account_placeholder":"請輸入教師職編或學生學號","admin_password":"管理員密碼","admin_password_placeholder":"請輸入管理員密碼",
        "remember":"記住我的帳號","login":"登入 Login","contact":"☎ 聯絡系辦","privacy":"本系統僅供亞洲大學心理學系教師與學生使用。",
        "public_label":"公開資訊與快速入口","schedule_title":"教室課表","schedule_sub":"查看課表與使用狀況","notice_title":"系統公告",
        "notice_sub":"重要通知與公告","guide_title":"使用說明","guide_sub":"操作手冊與指南","news_title":"最新消息","news_sub":"系統更新資訊",
        "reserve_message":"請先選擇教師或學生身分登入，再進行教室借用。","admin_message":"請選擇管理員身分並輸入管理員密碼。",
        "empty":"請輸入登入資料。","bad_admin":"管理員密碼錯誤。","bad_user":"身分驗證失敗，僅限心理學系教師及學生使用。",
        "back":"← 返回系統登入","date":"查詢日期","room":"教室","available":"可借用","course":"已排課","reserved":"已借用",
        "time_col":"時間","status_col":"狀態","detail_col":"說明","schedule_page":"教室課表與使用查詢","schedule_page_sub":"Classroom Schedule & Availability",
        "notice_page":"系統公告","notice_page_sub":"System Announcements","guide_page":"使用說明","guide_page_sub":"User Guide",
        "news_page":"最新消息","news_page_sub":"System Updates"
    },
    "English": {
        "dept":"Department of Psychology, Asia University","system":"Classroom Reservation and Inquiry System","subtitle":"AU Psychology Classroom Reservation System",
        "description":"An integrated platform for classroom reservations, availability inquiries, and administrative management.",
        "reserve_title":"Reserve a Classroom","reserve_sub":"Online request and conflict checking","query_title":"Availability Inquiry","query_sub":"View classroom availability instantly",
        "admin_title":"Administration","admin_sub":"Manage rosters, schedules, and reservations","login_title":"System Login","login_caption":"Select your role and enter your login information.",
        "role":"Role","faculty":"Faculty","student":"Student","admin":"Administrator","account_label":"Employee ID / Student ID",
        "account_placeholder":"Enter your employee ID or student ID","admin_password":"Administrator Password","admin_password_placeholder":"Enter the administrator password",
        "remember":"Remember my account","login":"Log In","contact":"☎ Contact Department Office","privacy":"This system is available only to Department of Psychology faculty and students.",
        "public_label":"Public Information and Quick Access","schedule_title":"Classroom Schedule","schedule_sub":"View schedules and room usage","notice_title":"System Announcements",
        "notice_sub":"Important notices and announcements","guide_title":"User Guide","guide_sub":"Instructions and operating guide","news_title":"Latest Updates","news_sub":"System release information",
        "reserve_message":"Please log in as faculty or student before submitting a classroom reservation.","admin_message":"Please select Administrator and enter the administrator password.",
        "empty":"Please enter your login information.","bad_admin":"Incorrect administrator password.","bad_user":"Identity verification failed. Access is limited to Department of Psychology faculty and students.",
        "back":"← Back to System Login","date":"Date","room":"Classroom","available":"Available","course":"Scheduled Course","reserved":"Reserved",
        "time_col":"Time","status_col":"Status","detail_col":"Details","schedule_page":"Classroom Schedule and Availability","schedule_page_sub":"Check course and reservation status by date and room.",
        "notice_page":"System Announcements","notice_page_sub":"Important notices and reservation policies","guide_page":"User Guide","guide_page_sub":"Instructions for faculty, students, and administrators",
        "news_page":"Latest Updates","news_page_sub":"System release notes and improvements"
    }
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
    """
    Export records safely to Excel.

    PostgreSQL TIMESTAMPTZ values are timezone-aware, while Excel does not
    support timezone-aware datetimes. Convert datetime columns to timezone-
    naive local values before calling DataFrame.to_excel().
    """
    buffer = io.BytesIO()
    frame = pd.DataFrame(rows).copy()

    for column in frame.columns:
        series = frame[column]

        # Handle pandas datetime dtypes, including datetime64[ns, tz].
        if pd.api.types.is_datetime64_any_dtype(series):
            try:
                if getattr(series.dt, "tz", None) is not None:
                    frame[column] = series.dt.tz_localize(None)
            except (AttributeError, TypeError):
                pass
            continue

        # Handle object columns containing Python datetime values returned
        # by SQLAlchemy / psycopg.
        if series.dtype == "object":
            def normalize_excel_value(value):
                if isinstance(value, datetime):
                    if value.tzinfo is not None and value.utcoffset() is not None:
                        return value.replace(tzinfo=None)
                    return value
                return value

            frame[column] = series.map(normalize_excel_value)

    safe_sheet = re.sub(r"[:\\/?*\[\]]", "_", str(sheet))[:31] or "資料"
    frame.to_excel(
        buffer,
        index=False,
        sheet_name=safe_sheet,
        engine="openpyxl",
    )
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
    .portal-label{{font-size:.72rem;color:#7a748a;margin-top:-4px;margin-bottom:5px;text-align:center}}
    div[data-testid="stButton"]>button[kind="secondary"]{{
        min-height:70px!important;
        background:#fff!important;
        border:1px solid var(--b)!important;
        color:#332d43!important;
        box-shadow:0 8px 22px rgba(67,34,160,.065)!important;
        text-align:left!important;
        justify-content:flex-start!important;
        padding:12px 16px!important;
        font-size:.93rem!important;
    }}
    div[data-testid="stButton"]>button[kind="secondary"]:hover{{
        border-color:#ad96f2!important;
        background:linear-gradient(100deg,#faf8ff,#f2edff)!important;
        color:#4d24bf!important;
        transform:translateY(-1px);
    }}
    .public-shell{{border:1px solid var(--b);border-radius:22px;background:rgba(255,255,255,.97);box-shadow:0 18px 44px rgba(55,25,145,.10);padding:22px 24px;margin-top:4px}}
    .public-title{{font-size:1.8rem;font-weight:900;color:var(--p);margin-bottom:5px}}
    .public-sub{{color:var(--m);margin-bottom:16px}}
    .notice-card{{border:1px solid var(--b);border-radius:16px;padding:15px 17px;background:#fff;margin:9px 0;box-shadow:0 6px 18px rgba(67,34,160,.045)}}
    .notice-card b{{color:#3c1aa5}}.notice-card p{{margin:6px 0 0;color:#666174;line-height:1.65}}
    .footer-note{{text-align:center;color:#827e92;font-size:.72rem;margin-top:14px}}
    @media(max-width:900px){{.features,.quick-grid{{grid-template-columns:1fr}}.logo-wrap{{height:auto}}.block-container{{padding-left:1rem!important;padding-right:1rem!important}}}}

    .mobile-nav-card{{
        border:1px solid var(--b);
        border-radius:18px;
        background:rgba(255,255,255,.97);
        box-shadow:0 10px 26px rgba(55,25,145,.08);
        padding:10px 13px 6px;
        margin:2px 0 18px;
    }}
    .mobile-nav-title{{
        font-size:.78rem;
        color:#6f6980;
        font-weight:800;
        margin:0 0 7px;
    }}
    @media(max-width:900px){{
        .features,.quick-grid{{grid-template-columns:1fr}}
        .logo-wrap{{height:auto}}
        .block-container{{padding-left:1rem!important;padding-right:1rem!important;padding-top:.8rem!important}}
        [data-testid="stSidebar"]{{display:none!important}}
        [data-testid="collapsedControl"]{{display:none!important}}
        .topbar{{padding:12px 16px}}
        .brand{{font-size:.96rem}}
        .brand span{{font-size:.69rem}}
        div[data-testid="stRadio"] div[role="radiogroup"]{{
            display:grid!important;
            grid-template-columns:1fr!important;
            gap:8px!important;
        }}
        div[data-testid="stRadio"] div[role="radiogroup"] label{{
            width:100%!important;
            margin:0!important;
            min-height:46px!important;
            display:flex!important;
            align-items:center!important;
            justify-content:flex-start!important;
            padding:.55rem .8rem!important;
        }}
    }}
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


def _set_public_page(page_name, message=""):
    st.session_state.public_page = page_name
    st.session_state.portal_message = message
    st.rerun()


def _availability_rows(query_date, query_room, language=None):
    language = language or st.session_state.get("language", "中文")
    p = PORTAL_TEXT[language]
    courses = get_course_blocks(str(query_date), query_room)
    bookings = get_bookings_by_date_room(
        str(query_date),
        query_room,
        status=None,
    )
    output = []
    for start_time, end_time in SLOTS:
        status, detail = p["available"], ""
        for course in courses:
            if start_time < str(course["end_time"])[:5] and end_time > str(course["start_time"])[:5]:
                status = p["course"]
                detail = course.get("course_name", "")
                if course.get("teacher"): detail += f" | {course['teacher']}"
                break
        if status == p["available"]:
            for booking in bookings:
                if start_time < str(booking["end_time"])[:5] and end_time > str(booking["start_time"])[:5]:
                    status, detail = p["reserved"], booking.get("reason", "")
                    break
        output.append({p["time_col"]: f"{start_time}–{end_time}", p["status_col"]: status, p["detail_col"]: detail})
    return output



@st.cache_resource(show_spinner=False)
def cached_initialize_database():
    return initialize_database_once()


@st.cache_data(ttl=60, show_spinner=False)
def cached_dashboard_counts():
    return get_dashboard_counts()


@st.cache_data(ttl=120, show_spinner=False)
def cached_database_health():
    return database_health_check()


@st.cache_data(ttl=120, show_spinner=False)
def cached_active_period():
    return get_active_open_period()


@st.cache_data(ttl=60, show_spinner=False)
def cached_course_semesters():
    return get_course_semesters()


@st.cache_data(ttl=45, show_spinner=False)
def cached_authorized_users():
    return get_all_authorized_users()


@st.cache_data(ttl=30, show_spinner=False)
def cached_recent_bookings(limit=300):
    return get_recent_bookings(limit)


@st.cache_data(ttl=30, show_spinner=False)
def cached_audit_logs(limit=300):
    return get_audit_logs(limit)


@st.cache_data(ttl=120, show_spinner=False)
def cached_announcements(active_only=True):
    if active_only:
        return get_active_announcements(limit=100)
    return get_all_announcements(limit=500)


@st.cache_data(ttl=120, show_spinner=False)
def cached_announcement_counts():
    return get_announcement_counts()


@st.cache_data(ttl=15, show_spinner=False)
def cached_pending_bookings(limit=500):
    return get_pending_bookings(limit)


@st.cache_data(ttl=60, show_spinner=False)
def cached_auto_approve_setting():
    return get_setting_bool("auto_approve_bookings", False)


def clear_data_cache():
    st.cache_data.clear()


def clear_announcement_cache():
    """Clear only announcement-related cached functions."""
    cached_announcements.clear()
    cached_announcement_counts.clear()


def render_public_schedule():
    topbar(language_selector=True)
    p = PORTAL_TEXT[st.session_state.language]
    st.markdown(f'<div class="public-shell"><div class="public-title">{p["schedule_page"]}</div><div class="public-sub">{p["schedule_page_sub"]}</div></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left: query_date = st.date_input(p["date"], value=date.today(), key="public_schedule_date")
    with right: query_room = st.selectbox(p["room"], ROOMS, key="public_schedule_room")
    frame = pd.DataFrame(_availability_rows(query_date, query_room, st.session_state.language))
    st.dataframe(frame, use_container_width=True, hide_index=True)
    status_col = p["status_col"]
    a,b,c = st.columns(3)
    a.metric(p["available"], int((frame[status_col] == p["available"]).sum()))
    b.metric(p["course"], int((frame[status_col] == p["course"]).sum()))
    c.metric(p["reserved"], int((frame[status_col] == p["reserved"]).sum()))
    if st.button(p["back"], use_container_width=True, key="back_schedule"):
        _set_public_page("login")
    return None


def render_public_announcements():
    topbar(language_selector=True)
    lang = st.session_state.language
    p = PORTAL_TEXT[lang]
    st.markdown(
        f'<div class="public-shell"><div class="public-title">{p["notice_page"]}</div>'
        f'<div class="public-sub">{p["notice_page_sub"]}</div></div>',
        unsafe_allow_html=True,
    )

    period = cached_active_period()
    if lang == "English":
        if period:
            st.success(
                f'Current semester: {period["semester"]} | '
                f'Reservation period: {period["start_date"]} – {period["end_date"]}'
            )
        else:
            st.warning("No classroom reservation period has been configured.")
    else:
        if period:
            st.success(
                f'目前開放學期：{period["semester"]}｜'
                f'借用期間：{period["start_date"]} ～ {period["end_date"]}'
            )
        else:
            st.warning("目前尚未設定教室借用開放期間。")

    notices = cached_announcements(True)
    if notices:
        for item in notices:
            title = item.get("title_en") if lang == "English" else item.get("title_zh")
            content = item.get("content_en") if lang == "English" else item.get("content_zh")
            title = title or item.get("title_zh") or "Announcement"
            content = content or item.get("content_zh") or ""
            category = item.get("category") or ""
            st.markdown(
                f'<div class="notice-card"><b>{category}｜{title}</b>'
                f'<p>{content}</p></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No current announcements." if lang == "English" else "目前沒有其他公告。")

    if lang == "English":
        st.markdown(
            '<div class="notice-card"><b>Reservation Date Rule</b>'
            '<p>Faculty and students may reserve classrooms only from the third day after the application date.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="notice-card"><b>借用日期規則</b>'
            '<p>教師及學生僅能申請送出當日 N+3 日起的教室時段。</p></div>',
            unsafe_allow_html=True,
        )

    if st.button(p["back"], use_container_width=True, key="back_notice"):
        _set_public_page("login")
    return None


def render_public_guide():
    topbar(language_selector=True)
    lang = st.session_state.language
    p = PORTAL_TEXT[lang]
    st.markdown(
        f'<div class="public-shell"><div class="public-title">{p["guide_page"]}</div>'
        f'<div class="public-sub">{p["guide_page_sub"]}</div></div>',
        unsafe_allow_html=True,
    )
    if lang == "English":
        tab1, tab2, tab3 = st.tabs(["Faculty / Students", "Administrators", "FAQ"])
        with tab1:
            st.markdown("""
### Reservation Steps
1. Select Faculty or Student and enter your employee ID or student ID.
2. Select a date, classroom, start time, and end time.
3. Enter your phone number, email, and purpose.
4. The system checks course and reservation conflicts automatically.
5. Save the reservation number after submission.
            """)
        with tab2:
            st.markdown("""
### Administrative Functions
- Import authorized rosters.
- Configure reservation periods.
- Import course schedules.
- View, export, modify, and cancel reservations.
- Review audit logs and database status.
            """)
        with tab3:
            st.markdown("""
**Unable to log in?**  
Confirm the role and check that your ID is in the authorized roster.

**Administrator password issue?**  
Contact psychology@asia.edu.tw.
            """)
    else:
        tab1, tab2, tab3 = st.tabs(["教師／學生", "管理員", "常見問題"])
        with tab1:
            st.markdown("""
### 教室借用步驟
1. 選擇教師或學生身分並輸入職編／學號。
2. 選擇日期、教室及起訖時間。
3. 填寫聯絡資訊與借用事由。
4. 系統自動檢查衝堂。
5. 保存申請完成後的借用編號。
            """)
        with tab2:
            st.markdown("""
### 管理端主要功能
- 匯入授權名冊。
- 設定借用期間。
- 匯入正式課表。
- 查看、匯出、修改及取消借用。
- 查閱操作紀錄。
            """)
        with tab3:
            st.markdown("""
**無法登入怎麼辦？**  
請確認身分與職編／學號是否已匯入授權名冊。

**管理員密碼問題？**  
請聯絡 psychology@asia.edu.tw。
            """)
    if st.button(p["back"], use_container_width=True, key="back_guide"):
        _set_public_page("login")
    return None


def render_public_news():
    topbar(language_selector=True)
    lang=st.session_state.language; p=PORTAL_TEXT[lang]
    st.markdown(f'<div class="public-shell"><div class="public-title">{p["news_page"]}</div><div class="public-sub">{p["news_page_sub"]}</div></div>', unsafe_allow_html=True)
    html = '<div class="notice-card"><b>V8.9 Full Bilingual Portal Edition</b><p>Complete English localization for homepage actions, login controls, and public pages. Updated the department contact email and removed the forgot-password option.</p></div>' if lang == "English" else '<div class="notice-card"><b>V8.9 Full Bilingual Portal Edition</b><p>首頁功能、登入表單與公開資訊頁面完整支援英文切換；更新系辦聯絡信箱並移除忘記密碼選項。</p></div>'
    st.markdown(html, unsafe_allow_html=True)
    if st.button(p["back"], use_container_width=True, key="back_news"):
        _set_public_page("login")
    return None


def login_page():
    topbar(language_selector=True)
    lang=st.session_state.language; p=PORTAL_TEXT[lang]
    portal_message=st.session_state.pop("portal_message", "")
    if portal_message:
        st.info(portal_message)
    left,right=st.columns([1.2,.86], gap="large", vertical_alignment="top")
    with left:
        logo_uri=image_data_uri(PSY_LOGO)
        logo_html=f'<div class="logo-wrap"><img class="brand-logo" src="{logo_uri}" alt="Department of Psychology logo"></div>' if logo_uri else '<div class="logo-wrap"><div class="logo-fallback">Ψ</div></div>'
        st.markdown(logo_html+f'<div class="hero"><div class="eyebrow">AU-PCRS · PROFESSIONAL ADMINISTRATIVE PORTAL</div><div class="t1">{p["dept"]}</div><div class="t2">{p["system"]}</div><div class="sub">{p["subtitle"]}</div><div class="desc">{p["description"]}</div></div>', unsafe_allow_html=True)
        f1,f2,f3=st.columns(3)
        with f1:
            if st.button(f'▣  {p["reserve_title"]}\n\n{p["reserve_sub"]}', use_container_width=True, key="feature_reserve"): _set_public_page("login",p["reserve_message"])
        with f2:
            if st.button(f'⌕  {p["query_title"]}\n\n{p["query_sub"]}', use_container_width=True, key="feature_query"): _set_public_page("schedule")
        with f3:
            if st.button(f'⚙  {p["admin_title"]}\n\n{p["admin_sub"]}', use_container_width=True, key="feature_admin"):
                st.session_state.preferred_role="管理員"; _set_public_page("login",p["admin_message"])
    with right:
        with st.container(border=True):
            st.markdown(f'<div class="login-title">{p["login_title"]}</div><div class="login-caption">{p["login_caption"]}</div><div class="rule"></div>', unsafe_allow_html=True)
            internal_roles=["教師","學生","管理員"]; display_roles=[p["faculty"],p["student"],p["admin"]]
            preferred=st.session_state.pop("preferred_role","教師"); default_index=internal_roles.index(preferred) if preferred in internal_roles else 0
            with st.form("login", clear_on_submit=False):
                display_role=st.radio(p["role"],display_roles,horizontal=True,index=default_index)
                role=internal_roles[display_roles.index(display_role)]; is_admin=role=="管理員"
                cred=st.text_input(p["admin_password"] if is_admin else p["account_label"], type="password" if is_admin else "default", placeholder=p["admin_password_placeholder"] if is_admin else p["account_placeholder"])
                st.checkbox(p["remember"])
                submitted=st.form_submit_button(p["login"], use_container_width=True)
            st.link_button(p["contact"], "mailto:psychology@asia.edu.tw?subject=AU-PCRS%20System%20Support", use_container_width=True)
            if submitted:
                if not cred.strip(): st.error(p["empty"])
                elif is_admin:
                    if cred==admin_password():
                        st.session_state.user={"user_type":"管理員","name":"Administrator","identification_code":"ADMIN","email":""}; st.session_state.admin=True; st.rerun()
                    else: st.error(p["bad_admin"])
                else:
                    user=verify_authorized_user_by_code(role,cred)
                    if user: st.session_state.user=user; st.session_state.admin=False; st.rerun()
                    else: st.error(p["bad_user"])
            st.markdown(f'<div class="privacy">{p["privacy"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="portal-label">{p["public_label"]}</div>', unsafe_allow_html=True)
    q1,q2,q3,q4=st.columns(4)
    with q1:
        if st.button(f'▦  {p["schedule_title"]}\n\n{p["schedule_sub"]}', use_container_width=True, key="quick_schedule"): _set_public_page("schedule")
    with q2:
        if st.button(f'◉  {p["notice_title"]}\n\n{p["notice_sub"]}', use_container_width=True, key="quick_notice"): _set_public_page("announcements")
    with q3:
        if st.button(f'▤  {p["guide_title"]}\n\n{p["guide_sub"]}', use_container_width=True, key="quick_guide"): _set_public_page("guide")
    with q4:
        if st.button(f'▥  {p["news_title"]}\n\n{p["news_sub"]}', use_container_width=True, key="quick_news"): _set_public_page("news")
    copyright_text="© 2026 Department of Psychology, Asia University" if lang=="English" else "© 2026 亞洲大學心理學系"
    st.markdown(f'<div class="footer-note">AU-PCRS V9.9 Mobile Navigation Fix Edition ｜ {copyright_text}</div>', unsafe_allow_html=True)
    return None


def render_dashboard() -> None:
    """Render the dashboard directly. Do not wrap this call in st.write()."""
    st.markdown("## 智慧儀表板 / Dashboard")
    counts = cached_dashboard_counts()
    a, b, c, d = st.columns(4)
    a.metric("教師 Faculty", counts["teachers"])
    b.metric("學生 Students", counts["students"])
    c.metric("進行中借用 Active", counts["active_bookings"])
    d.metric("專業教室 Rooms", len(ROOMS))
    period = cached_active_period()
    if period:
        st.success(f"目前開放：{period['semester']}｜{period['start_date']}～{period['end_date']}")
    else:
        st.warning("尚未設定開放借用期間")
    ok, message = cached_database_health()
    if ok:
        st.info(f"✅ Database：{message}")
    else:
        st.error(f"❌ Database：{message}")


def reserve():
    user = st.session_state.user
    lang = st.session_state.language
    is_english = lang == "English"
    earliest_date = date.today() + timedelta(days=3)

    receipt = st.session_state.pop("booking_receipt", None)
    if receipt:
        if receipt["status"] == "已核准":
            st.success(
                f"Application approved. Reservation No.: {receipt['booking_id']}"
                if is_english else
                f"申請已成功核准，借用編號：{receipt['booking_id']}"
            )
        else:
            st.success(
                f"Application submitted and pending review. Application No.: {receipt['booking_id']}"
                if is_english else
                f"申請已成功送出，待管理員審核。申請編號：{receipt['booking_id']}"
            )

    st.markdown("## Reserve a Classroom" if is_english else "## 我要借教室 / Reserve")
    st.info(
        f"Applicant: {user['name']} ({user['user_type']})"
        if is_english else
        f"登入者：{user['name']}（{user['user_type']}）"
    )
    st.caption(
        f"Earliest available reservation date: {earliest_date} (N+3 rule)"
        if is_english else
        f"最早可申請日期：{earliest_date}（送出當日 N+3 日）"
    )

    with st.form("booking"):
        left, right = st.columns(2)
        with left:
            booking_date = st.date_input(
                "Reservation Date" if is_english else "借用日期",
                value=earliest_date,
                min_value=earliest_date,
            )
            room = st.selectbox("Classroom" if is_english else "教室", ROOMS)
            start_time = st.selectbox("Start Time" if is_english else "開始時間", [x for x, _ in SLOTS])
            end_time = st.selectbox("End Time" if is_english else "結束時間", [x for _, x in SLOTS])
        with right:
            phone = st.text_input("Mobile Phone" if is_english else "聯絡手機")
            email = st.text_input("Email", value=user.get("email") or "")
            reason = st.text_area("Purpose" if is_english else "借用事由", height=160)
        submitted = st.form_submit_button(
            "Submit Application" if is_english else "送出申請",
            use_container_width=True,
        )

    if submitted:
        if booking_date < earliest_date:
            st.error(
                "The reservation date must be at least three days after today."
                if is_english else
                "借用日期必須為送出申請當日 N+3 日起。"
            )
            return
        if not phone.strip() or not email.strip() or not reason.strip():
            st.error("Please complete all required fields." if is_english else "請完整填寫必填欄位。")
            return
        if not valid_phone(phone) or not valid_email(email) or start_time >= end_time:
            st.error("Invalid input format." if is_english else "輸入格式不正確。")
            return

        period = cached_active_period()
        if not period or not (
            str(period["start_date"]) <= str(booking_date) <= str(period["end_date"])
        ):
            st.error(
                "The selected date is outside the reservation period."
                if is_english else
                "所選日期不在開放期間。"
            )
            return

        conflict = check_booking_conflict(str(booking_date), room, start_time, end_time)
        if conflict:
            existing = find_existing_booking(
                str(booking_date), room, start_time, end_time,
                user["identification_code"],
            )
            if existing:
                st.session_state["booking_receipt"] = {
                    "booking_id": existing["booking_id"],
                    "status": existing["status"],
                }
                st.rerun()
            st.error(
                f"Time conflict: {conflict['detail']}"
                if is_english else
                f"時段衝突：{conflict['detail']}"
            )
            return

        booking_id, booking_status = create_booking(
            str(booking_date),
            room,
            start_time,
            end_time,
            user["user_type"],
            user["name"],
            user["identification_code"],
            phone,
            email,
            reason,
        )
        clear_data_cache()
        st.session_state["booking_receipt"] = {
            "booking_id": booking_id,
            "status": booking_status,
        }
        st.rerun()


def query():
    st.markdown("## 教室查詢 / Availability")
    left, right = st.columns(2)
    with left:
        query_date = st.date_input("日期", value=date.today(), key="qd")
    with right:
        query_room = st.selectbox("教室", ROOMS, key="qr")
    st.dataframe(
        pd.DataFrame(_availability_rows(query_date, query_room)),
        use_container_width=True,
        hide_index=True,
    )


def admin_page():
    st.markdown("## 管理員後台 / Administration")

    section = st.radio(
        "管理功能 / Administration Menu",
        ["儀表板", "公告管理", "名冊管理", "開放期間", "課表管理", "借用審核", "借用管理", "操作紀錄"],
        horizontal=True,
        key="admin_section",
    )

    if section == "儀表板":
        _ = render_dashboard()
        return None

    if section == "公告管理":
        st.markdown("### 系統公告管理 / Announcement Management")
        counts = cached_announcement_counts()
        c1, c2 = st.columns(2)
        c1.metric("公告總數", counts["total"])
        c2.metric("目前發布中", counts["active"])

        try:
            rows = cached_announcements(False)
        except Exception:
            st.error("公告資料讀取失敗，請重新啟動系統後再試。")
            return None

        mode = st.radio("作業", ["新增公告", "修改／刪除公告"], horizontal=True)
        categories = ["一般公告", "開放時間", "重要通知", "系統維護"]

        if mode == "新增公告":
            with st.form("announcement_create"):
                title_zh = st.text_input("中文標題")
                title_en = st.text_input("English Title")
                content_zh = st.text_area("中文內容", height=130)
                content_en = st.text_area("English Content", height=130)
                category = st.selectbox("公告類別", categories)
                c1, c2 = st.columns(2)
                with c1:
                    publish_start = st.date_input("公告開始日", value=date.today())
                with c2:
                    publish_end = st.date_input(
                        "公告結束日",
                        value=date.today() + timedelta(days=30),
                    )
                is_published = st.checkbox("立即發布", value=True)
                submitted = st.form_submit_button("新增公告", use_container_width=True)

            if submitted:
                if not title_zh.strip() or not content_zh.strip():
                    st.error("中文標題與中文內容為必填。")
                elif publish_start > publish_end:
                    st.error("公告結束日不得早於開始日。")
                else:
                    try:
                        announcement_id = create_announcement(
                            title_zh, content_zh, title_en, content_en,
                            category, publish_start, publish_end, is_published,
                        )
                        clear_announcement_cache()
                        st.success(f"公告已新增，編號：{announcement_id}")
                        st.rerun()
                    except Exception as exc:
                        st.error("公告新增失敗，請確認資料內容後再試；系統已使用新版公告資料表。")
                        st.caption(str(exc))
        else:
            if not rows:
                st.info("目前尚無公告。")
                return None

            labels = {
                row["id"]: f'#{row["id"]}｜{row.get("category","")}｜{row.get("title_zh","")}'
                for row in rows
            }
            selected_id = st.selectbox(
                "選擇公告",
                list(labels.keys()),
                format_func=lambda value: labels[value],
            )
            item = next(row for row in rows if row["id"] == selected_id)

            with st.form("announcement_edit"):
                title_zh = st.text_input("中文標題", value=item.get("title_zh") or "")
                title_en = st.text_input("English Title", value=item.get("title_en") or "")
                content_zh = st.text_area("中文內容", value=item.get("content_zh") or "", height=130)
                content_en = st.text_area("English Content", value=item.get("content_en") or "", height=130)
                category = st.selectbox(
                    "公告類別",
                    categories,
                    index=categories.index(item.get("category"))
                    if item.get("category") in categories else 0,
                )
                c1, c2 = st.columns(2)
                with c1:
                    publish_start = st.date_input(
                        "公告開始日",
                        value=item.get("publish_start") or date.today(),
                        key="edit_publish_start",
                    )
                with c2:
                    publish_end = st.date_input(
                        "公告結束日",
                        value=item.get("publish_end") or (date.today() + timedelta(days=30)),
                        key="edit_publish_end",
                    )
                is_published = st.checkbox(
                    "發布中",
                    value=bool(item.get("is_published")),
                )
                save = st.form_submit_button("儲存修改", use_container_width=True)

            if save:
                if not title_zh.strip() or not content_zh.strip():
                    st.error("中文標題與中文內容為必填。")
                elif publish_start > publish_end:
                    st.error("公告結束日不得早於開始日。")
                else:
                    update_announcement(
                        selected_id, title_zh, content_zh, title_en, content_en,
                        category, publish_start, publish_end, is_published,
                    )
                    clear_announcement_cache()
                    st.success("公告已更新。")
                    st.rerun()

            confirm_delete = st.checkbox("我確認要刪除此公告")
            if st.button("刪除公告", type="secondary", use_container_width=True):
                if not confirm_delete:
                    st.error("請先勾選刪除確認。")
                else:
                    delete_announcement(selected_id)
                    clear_announcement_cache()
                    st.warning("公告已刪除。")
                    st.rerun()

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        return None

    if section == "名冊管理":
        user_type = st.radio("名冊類別", ["教師", "學生"], horizontal=True)
        upload = st.file_uploader(
            "Excel欄位：辨識碼、姓名、聯絡信箱、狀態",
            type=["xlsx"],
            key="roster_upload",
        )
        replace = st.checkbox("覆蓋此類既有名冊")
        if st.button("匯入名冊", use_container_width=True):
            if upload is None:
                st.error("請先選擇Excel檔案。")
            else:
                try:
                    result = import_authorized_users(
                        pd.read_excel(upload, dtype=str).fillna(""),
                        user_type,
                        replace,
                    )
                    clear_data_cache()
                    st.success(f"匯入完成：{result}")
                except Exception as exc:
                    st.error(f"匯入失敗：{exc}")

        rows = cached_authorized_users()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無名冊資料。")
        return None

    if section == "開放期間":
        current = cached_active_period()
        if current:
            st.info(
                f"目前：{current['semester']}｜"
                f"{current['start_date']} ～ {current['end_date']}"
            )

        left, right = st.columns(2)
        with left:
            start_date = st.date_input("開始日期", value=date.today(), key="period_start")
        with right:
            end_date = st.date_input("結束日期", value=date.today(), key="period_end")
        semester = st.text_input("學期", value=current["semester"] if current else "115-1")

        if st.button("儲存並啟用", use_container_width=True):
            if start_date > end_date:
                st.error("結束日期不得早於開始日期。")
            else:
                save_open_period(semester, str(start_date), str(end_date))
                clear_data_cache()
                st.success("開放期間已儲存。")

        st.divider()
        st.markdown("### 借用審核模式")
        current_auto = cached_auto_approve_setting()
        auto_approve = st.toggle(
            "符合規則且無衝突時自動核准",
            value=current_auto,
            help="關閉時，所有申請先進入待審核；開啟時，通過日期、開放期間及衝堂檢查後立即核准。",
        )
        if auto_approve != current_auto:
            set_setting("auto_approve_bookings", str(bool(auto_approve)).lower())
            clear_data_cache()
            st.success("審核模式已更新。")
            st.rerun()

        st.caption("系統開放時間的文字公告，可至「公告管理」新增或修改，公告類別選擇「開放時間」。")
        return None

    if section == "課表管理":
        semester = st.text_input("匯入學期", value="115-1", key="course_semester")
        replace = st.checkbox("清除此學期既有課表")
        upload = st.file_uploader("課表Excel", type=["xlsx"], key="course_upload")

        if upload is not None:
            frame = pd.read_excel(upload, dtype=str).fillna("")
            st.dataframe(frame.head(20), use_container_width=True, hide_index=True)
            if st.button("確認匯入課表", use_container_width=True):
                try:
                    result = add_course_blocks(frame, semester, replace)
                    clear_data_cache()
                    st.success(result)
                except Exception as exc:
                    st.error(f"匯入失敗：{exc}")

        semesters = cached_course_semesters()
        if semesters:
            st.dataframe(pd.DataFrame(semesters), use_container_width=True, hide_index=True)
            selected = st.selectbox("選擇學期", [row["semester"] for row in semesters])
            a, b, c = st.columns(3)
            if a.button("啟用學期", use_container_width=True):
                set_course_semester_active(selected, True)
                clear_data_cache()
                st.success("已啟用。")
            if b.button("停用學期", use_container_width=True):
                set_course_semester_active(selected, False)
                clear_data_cache()
                st.warning("已停用。")
            if c.button("刪除學期", use_container_width=True):
                count = delete_course_semester(selected)
                clear_data_cache()
                st.warning(f"已刪除 {count} 筆課表資料。")
        else:
            st.info("目前尚無課表資料。")
        return None

    if section == "借用審核":
        st.markdown("### 借用申請審核 / Reservation Review")
        auto_mode = cached_auto_approve_setting()
        if auto_mode:
            st.info("目前為自動核准模式；符合規則且無衝突的申請會立即核准。")
        else:
            st.warning("目前為人工審核模式；所有新申請將先列為待審核。")

        pending = cached_pending_bookings(500)
        if not pending:
            st.success("目前沒有待審核申請。")
            return None

        st.dataframe(pd.DataFrame(pending), use_container_width=True, hide_index=True)
        labels = {
            row["booking_id"]: (
                f'{row["booking_id"]}｜{row["booking_date"]}｜'
                f'{row["room"]}｜{row["applicant_name"]}'
            )
            for row in pending
        }
        booking_id = st.selectbox(
            "選擇待審核申請",
            list(labels.keys()),
            format_func=lambda value: labels[value],
        )
        item = next(row for row in pending if row["booking_id"] == booking_id)
        st.markdown(
            f"**借用人：** {item['applicant_name']}（{item['applicant_type']}）  \n"
            f"**日期時間：** {item['booking_date']} "
            f"{str(item['start_time'])[:5]}–{str(item['end_time'])[:5]}  \n"
            f"**教室：** {item['room']}  \n"
            f"**事由：** {item['reason']}"
        )
        note = st.text_area("審核備註")
        approve_col, reject_col = st.columns(2)
        if approve_col.button("核准申請", use_container_width=True):
            conflict = check_booking_conflict(
                str(item["booking_date"]),
                item["room"],
                str(item["start_time"])[:5],
                str(item["end_time"])[:5],
                exclude_booking_id=booking_id,
            )
            if conflict:
                st.error(f"目前已有衝突，無法核准：{conflict['detail']}")
            else:
                review_booking(booking_id, "已核准", "Administrator", note)
                clear_data_cache()
                st.success("申請已核准。")
                st.rerun()

        if reject_col.button("退回申請", use_container_width=True):
            if not note.strip():
                st.error("退回申請時請填寫原因。")
            else:
                review_booking(booking_id, "已退回", "Administrator", note)
                clear_data_cache()
                st.warning("申請已退回。")
                st.rerun()
        return None

    if section == "借用管理":
        limit = st.selectbox("顯示最近紀錄", [100, 300, 500, 1000], index=1)
        rows = cached_recent_bookings(limit)
        if not rows:
            st.info("目前尚無借用紀錄。")
            return None

        frame = pd.DataFrame(rows)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button(
            "匯出 Excel",
            xlsx(rows, "借用紀錄"),
            f"bookings_{date.today()}.xlsx",
            use_container_width=True,
        )

        booking_id = st.selectbox("選擇借用編號", [r["booking_id"] for r in rows])
        item = get_booking_by_id(booking_id)

        if item:
            with st.expander("修改借用資料"):
                new_date = st.date_input("借用日期", value=item["booking_date"])
                new_room = st.selectbox("教室", ROOMS, index=ROOMS.index(item["room"]))
                starts = [s for s, _ in SLOTS]
                ends = [e for _, e in SLOTS]
                current_start = str(item["start_time"])[:5]
                current_end = str(item["end_time"])[:5]
                new_start = st.selectbox(
                    "開始時間",
                    starts,
                    index=starts.index(current_start) if current_start in starts else 0,
                )
                new_end = st.selectbox(
                    "結束時間",
                    ends,
                    index=ends.index(current_end) if current_end in ends else 0,
                )
                new_reason = st.text_area("借用事由", value=item["reason"])

                if st.button("儲存修改"):
                    conflict = check_booking_conflict(
                        str(new_date),
                        new_room,
                        new_start,
                        new_end,
                        exclude_booking_id=booking_id,
                    )
                    if conflict:
                        st.error(f"時段衝突：{conflict['detail']}")
                    else:
                        update_booking(
                            booking_id,
                            str(new_date),
                            new_room,
                            new_start,
                            new_end,
                            new_reason,
                        )
                        clear_data_cache()
                        st.success("借用資料已更新。")

            cancel_reason = st.text_input("取消原因")
            if st.button("取消借用") and cancel_reason.strip():
                cancel_booking(booking_id, cancel_reason.strip())
                clear_data_cache()
                st.success("借用已取消。")
                st.rerun()
        return None

    if section == "操作紀錄":
        limit = st.selectbox("顯示最近紀錄", [100, 300, 500, 1000], index=1, key="audit_limit")
        logs = cached_audit_logs(limit)
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無操作紀錄。")
        return None

    return None


st.set_page_config(page_title="AU-PCRS V9.9", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
for key, value in {"language": "中文", "user": None, "admin": False, "public_page": "login", "portal_message": ""}.items():
    if key not in st.session_state:
        st.session_state[key] = value

try:
    cached_initialize_database()
except Exception as exc:
    style(login_mode=True)
    st.error("資料庫初始化失敗")
    st.caption(str(exc))
    st.stop()

if st.session_state.user is None:
    style(login_mode=True)
    public_page = st.session_state.get("public_page", "login")
    if public_page == "schedule":
        _ = render_public_schedule()
    elif public_page == "announcements":
        _ = render_public_announcements()
    elif public_page == "guide":
        _ = render_public_guide()
    elif public_page == "news":
        _ = render_public_news()
    else:
        _ = login_page()
    st.stop()

style(login_mode=False)

t = TXT[st.session_state.language]
if st.session_state.admin:
    pages = [t["home"], t["adminp"]]
else:
    pages = [t["home"], t["reserve"], t["query"]]

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

    st.caption("AU-PCRS V9.9")
    st.caption("Mobile Navigation Fix Edition")
    if st.button(t["logout"], use_container_width=True, key="sidebar_logout"):
        st.session_state.user = None
        st.session_state.admin = False
        st.session_state.pop("main_page", None)
        st.rerun()

topbar(language_selector=False)

st.markdown(
    '<div class="mobile-nav-card"><div class="mobile-nav-title">'
    '功能選單 / Navigation</div></div>',
    unsafe_allow_html=True,
)

if "main_page" not in st.session_state or st.session_state.main_page not in pages:
    st.session_state.main_page = pages[0]

page = st.radio(
    "功能選單 / Navigation",
    pages,
    index=pages.index(st.session_state.main_page),
    horizontal=True,
    key="main_navigation_radio",
    label_visibility="collapsed",
)
st.session_state.main_page = page

mobile_left, mobile_right = st.columns([1.7, 1])
with mobile_left:
    mobile_language = st.selectbox(
        "語言 / Language",
        ["中文", "English"],
        index=0 if st.session_state.language == "中文" else 1,
        key="main_language",
        label_visibility="collapsed",
    )
    if mobile_language != st.session_state.language:
        st.session_state.language = mobile_language
        st.rerun()

with mobile_right:
    if st.button(t["logout"], use_container_width=True, key="main_logout"):
        st.session_state.user = None
        st.session_state.admin = False
        st.session_state.pop("main_page", None)
        st.rerun()

st.divider()

if page == t["home"]:
    _ = render_dashboard()
elif page == t["reserve"]:
    _ = reserve()
elif page == t["query"]:
    _ = query()
else:
    _ = admin_page()
