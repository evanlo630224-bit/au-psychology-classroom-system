import io, os, re
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st

from database import (
    add_course_blocks, cancel_booking, check_booking_conflict, create_booking,
    database_health_check, delete_course_semester, get_active_open_period,
    get_all_authorized_users, get_all_bookings, get_audit_logs,
    get_booking_by_id, get_course_blocks, get_course_semesters,
    get_dashboard_counts, import_authorized_users, init_db,
    save_open_period, set_course_semester_active, update_booking,
    verify_authorized_user_by_code,
)

BASE_DIR = Path(__file__).parent
PSY_LOGO = BASE_DIR / "assets" / "psychology_logo.jpg"
AU_LOGO = BASE_DIR / "assets" / "asia_university_logo.png"
ROOMS = ["M502", "M506", "M507", "M510", "800A"]
SLOTS = [("08:10","09:00"),("09:10","10:00"),("10:10","11:00"),("11:10","12:00"),("12:10","13:00"),("13:10","14:00"),("14:10","15:00"),("15:10","16:00"),("16:10","17:00"),("17:10","18:00"),("18:25","19:10"),("19:10","19:55"),("20:00","20:45"),("20:50","21:35"),("21:35","22:20")]

TXT = {
"中文": {"t1":"亞洲大學心理學系","t2":"專業教室借用及查詢系統","sub":"AU Psychology Classroom Reservation System","login":"系統登入","hint":"請選擇身分並輸入辨識碼","faculty":"教師","student":"學生","admin":"管理員","code":"教師職編／學生學號","pwd":"管理員密碼","go":"登入","logout":"登出","home":"首頁","reserve":"我要借教室","query":"教室查詢","adminp":"管理員後台","invalid":"身分驗證失敗，僅限心理學系教師及學生使用。","badpwd":"管理員密碼錯誤。","date":"借用日期","room":"教室","start":"開始時間","end":"結束時間","phone":"聯絡手機","email":"聯絡信箱","reason":"借用事由","submit":"送出申請","available":"可借用","course":"已排課","reserved":"已借用","privacy":"本系統僅供亞洲大學心理學系教師與學生使用，資料僅供教室借用及行政管理用途。"},
"English": {"t1":"Asia University Department of Psychology","t2":"Classroom Reservation and Inquiry System","sub":"亞洲大學心理學系專業教室借用及查詢系統","login":"System Login","hint":"Select your role and enter your identification code","faculty":"Faculty","student":"Student","admin":"Administrator","code":"Employee ID / Student ID","pwd":"Administrator Password","go":"Log In","logout":"Log Out","home":"Home","reserve":"Reserve a Classroom","query":"Check Availability","adminp":"Admin Panel","invalid":"Identity verification failed. This system is limited to Psychology faculty and students.","badpwd":"Incorrect administrator password.","date":"Reservation Date","room":"Classroom","start":"Start Time","end":"End Time","phone":"Mobile Phone","email":"Email","reason":"Purpose","submit":"Submit","available":"Available","course":"Course","reserved":"Reserved","privacy":"This system is for Asia University Department of Psychology faculty and students only. Data is used solely for classroom reservation and administration."}
}

def admin_password():
    try:
        if "ADMIN_PASSWORD" in st.secrets: return str(st.secrets["ADMIN_PASSWORD"])
        if "admin" in st.secrets and "password" in st.secrets["admin"]: return str(st.secrets["admin"]["password"])
    except Exception: pass
    return os.getenv("ADMIN_PASSWORD", "admin123")

def valid_email(v): return re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", v.strip()) is not None
def valid_phone(v): return len(re.sub(r"\D", "", v)) >= 8

def xlsx(rows, sheet="資料"):
    b=io.BytesIO(); pd.DataFrame(rows).to_excel(b,index=False,sheet_name=sheet,engine="openpyxl"); return b.getvalue()

def style():
    st.markdown("""<style>
    :root{--p:#4B2BD7;--pd:#2F1A96}.stApp{background:radial-gradient(circle at top right,rgba(75,43,215,.08),transparent 28%),#fff}
    [data-testid=stSidebar]{background:linear-gradient(180deg,#35188E,#5630D8)}[data-testid=stSidebar] *{color:white!important}
    .hero{padding:22px 28px;border:1px solid #e5dfff;border-radius:22px;background:#fff;box-shadow:0 12px 34px rgba(75,43,215,.08)}
    .h1{font-size:clamp(1.8rem,3vw,3rem);font-weight:850;color:var(--pd);line-height:1.1}.h2{font-size:clamp(1.5rem,2.5vw,2.5rem);font-weight:780;margin-top:8px}.sub{margin-top:9px;color:#6d6781}.pill{display:inline-block;margin-top:10px;padding:5px 12px;border-radius:999px;background:#ece7ff;color:#35188e;font-weight:700}
    div[data-testid=stMetric]{border:1px solid #e5dfff;border-radius:16px;padding:14px;background:#fff;box-shadow:0 8px 22px rgba(75,43,215,.06)}
    .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700}
    </style>""", unsafe_allow_html=True)

def header(t):
    a,b,c=st.columns([1.1,4.5,1.1],vertical_alignment="center")
    with a:
        if PSY_LOGO.exists(): st.image(str(PSY_LOGO),width=145)
    with b:
        st.markdown(f'<div class="hero"><div class="h1">{t["t1"]}</div><div class="h2">{t["t2"]}</div><div class="sub">{t["sub"]}</div><div class="pill">AU-PCRS V2.0 Cloud</div></div>',unsafe_allow_html=True)
    with c:
        if AU_LOGO.exists(): st.image(str(AU_LOGO),width=140)

def login(t):
    st.markdown(f"## {t['login']}"); st.caption(t['hint'])
    with st.form("login"):
        role=st.radio("身分 / Role",[t['faculty'],t['student'],t['admin']],horizontal=True)
        cred=st.text_input(t['pwd'] if role==t['admin'] else t['code'],type="password" if role==t['admin'] else "default")
        ok=st.form_submit_button(t['go'],use_container_width=True)
    if ok:
        if role==t['admin']:
            if cred==admin_password(): st.session_state.user={"user_type":"管理員","name":"Administrator","identification_code":"ADMIN","email":""}; st.session_state.admin=True; st.rerun()
            st.error(t['badpwd'])
        else:
            u=verify_authorized_user_by_code("教師" if role==t['faculty'] else "學生",cred)
            if u: st.session_state.user=u; st.session_state.admin=False; st.rerun()
            st.error(t['invalid'])
    st.caption(t['privacy'])

def home():
    c=get_dashboard_counts(); a,b,c1,d=st.columns(4); a.metric("Faculty / 教師",c["teachers"]); b.metric("Students / 學生",c["students"]); c1.metric("Active / 有效借用",c["active_bookings"]); d.metric("Rooms / 教室",len(ROOMS))
    p=get_active_open_period(); st.success(f"{p['semester']}｜{p['start_date']}～{p['end_date']}") if p else st.warning("No active reservation period / 尚未設定開放期間")
    ok,msg=database_health_check(); st.info(f"✅ Database: {msg}") if ok else st.error(msg)

def reserve(t):
    u=st.session_state.user; st.success(f"{u['name']}（{u['user_type']}）")
    with st.form("booking"):
        l,r=st.columns(2)
        with l: bd=st.date_input(t['date'],value=date.today(),min_value=date.today()); room=st.selectbox(t['room'],ROOMS); start=st.selectbox(t['start'],[s for s,_ in SLOTS]); end=st.selectbox(t['end'],[e for _,e in SLOTS])
        with r: phone=st.text_input(t['phone']); email=st.text_input(t['email'],value=u.get('email') or ''); reason=st.text_area(t['reason'])
        go=st.form_submit_button(t['submit'],use_container_width=True)
    if go:
        if not phone.strip() or not email.strip() or not reason.strip(): st.error("Please complete all required fields / 請完整填寫必填欄位"); return
        if not valid_phone(phone) or not valid_email(email) or start>=end: st.error("Invalid input / 輸入格式不正確"); return
        p=get_active_open_period()
        if not p or not (str(p['start_date'])<=str(bd)<=str(p['end_date'])): st.error("Outside reservation period / 不在開放期間"); return
        cf=check_booking_conflict(str(bd),room,start,end)
        if cf: st.error("Time conflict / 時段衝突"); st.caption(cf['detail']); return
        bid=create_booking(str(bd),room,start,end,u['user_type'],u['name'],u['identification_code'],phone.strip(),email.strip(),reason.strip()); st.success(f"Reservation ID / 借用編號：{bid}")

def query(t):
    a,b=st.columns(2)
    with a: qd=st.date_input(t['date'],value=date.today(),key="qd")
    with b: qr=st.selectbox(t['room'],ROOMS,key="qr")
    cs=get_course_blocks(str(qd),qr); bs=[x for x in get_all_bookings() if str(x['booking_date'])==str(qd) and x['room']==qr and x['status']=='有效']
    out=[]
    for s,e in SLOTS:
        status,detail=t['available'],''
        for c in cs:
            if s<str(c['end_time'])[:5] and e>str(c['start_time'])[:5]: status,detail=t['course'],c['course_name']; break
        if status==t['available']:
            for x in bs:
                if s<str(x['end_time'])[:5] and e>str(x['start_time'])[:5]: status,detail=t['reserved'],''; break
        out.append({"Time / 時間":f"{s}–{e}","Status / 狀態":status,"Detail / 說明":detail})
    st.dataframe(pd.DataFrame(out),use_container_width=True,hide_index=True)

def admin():
    tabs=st.tabs(["Dashboard","Roster / 名冊","Open Period / 開放期間","Schedule / 課表","Bookings / 借用管理","Audit / 操作紀錄"])
    with tabs[0]: home()
    with tabs[1]:
        typ=st.radio("名冊類別",["教師","學生"],horizontal=True); up=st.file_uploader("Excel：辨識碼、姓名、聯絡信箱、狀態",type=['xlsx'],key='roster'); rep=st.checkbox("覆蓋此類名冊")
        if st.button("匯入名冊"):
            if up is None: st.error("請先選擇檔案")
            else: st.success(import_authorized_users(pd.read_excel(up,dtype=str).fillna(''),typ,rep))
        rows=get_all_authorized_users(); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True) if rows else None
    with tabs[2]:
        a,b=st.columns(2)
        with a: sd=st.date_input("開始日期",value=date.today(),key='sd')
        with b: ed=st.date_input("結束日期",value=date.today(),key='ed')
        sem=st.text_input("學期",value='115-1')
        if st.button("儲存並啟用"): save_open_period(sem,str(sd),str(ed)); st.success("已儲存")
    with tabs[3]:
        sem=st.text_input("匯入學期",value='115-1',key='sem'); rep=st.checkbox("清除此學期既有課表"); up=st.file_uploader("課表 Excel",type=['xlsx'],key='course')
        if up is not None:
            df=pd.read_excel(up,dtype=str).fillna(''); st.dataframe(df.head(20),use_container_width=True,hide_index=True)
            if st.button("確認匯入課表"): st.success(add_course_blocks(df,sem,rep))
        ss=get_course_semesters(); st.dataframe(pd.DataFrame(ss),use_container_width=True,hide_index=True) if ss else None
    with tabs[4]:
        rows=get_all_bookings()
        if rows:
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); st.download_button("匯出 Excel",xlsx(rows,"借用紀錄"),f"bookings_{date.today()}.xlsx")
            bid=st.selectbox("借用編號",[r['booking_id'] for r in rows]); item=get_booking_by_id(bid)
            reason=st.text_input("取消原因")
            if st.button("取消借用") and reason.strip(): cancel_booking(bid,reason.strip()); st.rerun()
        else: st.info("目前尚無借用紀錄")
    with tabs[5]:
        logs=get_audit_logs(); st.dataframe(pd.DataFrame(logs),use_container_width=True,hide_index=True) if logs else st.info("目前尚無操作紀錄")

st.set_page_config(page_title="AU-PCRS",layout="wide"); style()
for k,v in {"language":"中文","user":None,"admin":False}.items():
    if k not in st.session_state: st.session_state[k]=v
try: init_db()
except Exception as exc: st.error("Database initialization failed / 資料庫初始化失敗"); st.caption(str(exc)); st.stop()
lang=st.sidebar.selectbox("語言 / Language",["中文","English"],index=0 if st.session_state.language=="中文" else 1); st.session_state.language=lang; t=TXT[lang]; header(t)
if st.session_state.user is None: login(t); st.stop()
with st.sidebar:
    st.markdown(f"### {st.session_state.user['name']}")
    if st.button(t['logout'],use_container_width=True): st.session_state.user=None; st.session_state.admin=False; st.rerun()
page=st.sidebar.radio("Menu / 選單",[t['home'],t['adminp']] if st.session_state.admin else [t['home'],t['reserve'],t['query']])
if page==t['home']: home()
elif page==t['reserve']: reserve(t)
elif page==t['query']: query(t)
else: admin()
