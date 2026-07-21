import io, os, re
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st
from database import *

BASE_DIR=Path(__file__).parent
PSY_LOGO=BASE_DIR/'assets'/'psychology_logo.jpg'
AU_LOGO=BASE_DIR/'assets'/'asia_university_logo.png'
ROOMS=['M502','M506','M507','M510','800A']
SLOTS=[('08:10','09:00'),('09:10','10:00'),('10:10','11:00'),('11:10','12:00'),('12:10','13:00'),('13:10','14:00'),('14:10','15:00'),('15:10','16:00'),('16:10','17:00'),('17:10','18:00'),('18:25','19:10'),('19:10','19:55'),('20:00','20:45'),('20:50','21:35'),('21:35','22:20')]
TXT={'中文':{'faculty':'教師','student':'學生','admin':'管理員','home':'首頁','reserve':'我要借教室','query':'教室查詢','adminp':'管理員後台','logout':'登出'},'English':{'faculty':'Faculty','student':'Student','admin':'Administrator','home':'Home','reserve':'Reserve a Classroom','query':'Check Availability','adminp':'Admin Panel','logout':'Log Out'}}

def admin_password():
    try:
        if 'ADMIN_PASSWORD' in st.secrets:return str(st.secrets['ADMIN_PASSWORD'])
        if 'admin' in st.secrets and 'password' in st.secrets['admin']:return str(st.secrets['admin']['password'])
    except Exception:pass
    return os.getenv('ADMIN_PASSWORD','admin123')
def valid_email(v):return re.fullmatch(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',v.strip()) is not None
def valid_phone(v):return len(re.sub(r'\D','',v))>=8
def xlsx(rows,sheet='資料'):
    b=io.BytesIO();pd.DataFrame(rows).to_excel(b,index=False,sheet_name=sheet,engine='openpyxl');return b.getvalue()
def style():
    st.markdown('''<style>
    :root{--p:#3c1aa5;--v:#5d32dc;--l:#f5f2ff;--b:#e8e2fb;--i:#252536;--m:#747287}
    html,body,[class*=css]{font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif}.stApp{background:radial-gradient(circle at 5% 82%,rgba(90,48,220,.09),transparent 24%),radial-gradient(circle at 95% 12%,rgba(90,48,220,.10),transparent 28%),linear-gradient(180deg,#fbfaff,#fff 68%)}
    header[data-testid=stHeader]{background:transparent}#MainMenu,footer{visibility:hidden}.block-container{max-width:1500px;padding-top:1rem;padding-bottom:2rem}
    [data-testid=stSidebar]{background:linear-gradient(180deg,#2d117f,#4f25cc 54%,#6a3ce5)}[data-testid=stSidebar] *{color:white!important}
    .topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;border-radius:18px;background:linear-gradient(110deg,#2f1288,#5c31d5);color:#fff;box-shadow:0 14px 36px rgba(55,25,145,.18);margin-bottom:24px}.brand{font-weight:850;font-size:1.05rem}.brand span{display:block;font-size:.76rem;font-weight:500;opacity:.82;margin-top:3px}.chip{padding:7px 12px;border:1px solid rgba(255,255,255,.28);border-radius:999px;font-weight:700}
    .hero{padding:25px 12px}.eyebrow{color:var(--v);font-weight:850;letter-spacing:.12em;font-size:.8rem}.t1{font-size:clamp(2rem,4vw,3.6rem);font-weight:900;color:var(--p);line-height:1.13;margin:12px 0 8px}.t2{font-size:clamp(1.5rem,2.6vw,2.5rem);font-weight:850;color:var(--i)}.sub{font-size:1.1rem;color:#6e6b80;margin-top:14px}.desc{font-size:1.02rem;color:#464456;line-height:1.8;margin:25px 0}.features{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.feature,.quick,.card{background:#fff;border:1px solid var(--b);border-radius:16px;padding:15px;box-shadow:0 8px 22px rgba(67,34,160,.07)}.feature b{display:block;margin-bottom:4px}.feature span,.quick p{font-size:.78rem;color:var(--m)}
    .login{padding:28px 31px 22px;border:1px solid var(--b);border-radius:26px;background:rgba(255,255,255,.97);box-shadow:0 24px 60px rgba(55,25,145,.14)}.login-title{font-size:2rem;font-weight:900;color:var(--p)}.rule{width:42px;height:3px;border-radius:99px;background:linear-gradient(90deg,#7547ed,#3d1aa6);margin:10px 0 18px}
    .stTextInput input,.stTextArea textarea,.stDateInput input{border-radius:12px!important;border:1px solid #ddd7ef!important;background:#fcfbff!important}.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{border-radius:12px!important;font-weight:800!important}.stFormSubmitButton>button{min-height:3rem;background:linear-gradient(100deg,#6736dd,#3d19ad)!important;color:#fff!important;border:0!important}
    div[data-testid=stMetric]{border:1px solid var(--b);border-radius:18px;padding:15px;background:#fff;box-shadow:0 10px 24px rgba(66,34,157,.07)}.quick-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:24px}.footer-note{text-align:center;color:#827e92;font-size:.8rem;margin-top:28px}@media(max-width:900px){.features,.quick-grid{grid-template-columns:1fr}}
    </style>''',unsafe_allow_html=True)
def topbar():
    st.markdown(f'''<div class="topbar"><div class="brand">亞洲大學心理學系<span>Department of Psychology, Asia University</span></div><div class="chip">◎ 中文 / English</div></div>''',unsafe_allow_html=True)
def login_page():
    topbar();left,right=st.columns([1.22,.88],gap='large')
    with left:
        if PSY_LOGO.exists():st.image(str(PSY_LOGO),width=150)
        st.markdown('''<div class="hero"><div class="eyebrow">AU-PCRS · PROFESSIONAL ADMINISTRATIVE PORTAL</div><div class="t1">亞洲大學心理學系</div><div class="t2">專業教室借用及查詢系統</div><div class="sub">AU Psychology Classroom Reservation System</div><div class="desc">提供教師、學生與管理者進行教室借用、查詢與行政管理之整合平台。</div><div class="features"><div class="feature"><b>▣ 教室借用</b><span>線上申請與衝堂檢核</span></div><div class="feature"><b>⌕ 借用查詢</b><span>即時查看教室使用狀態</span></div><div class="feature"><b>⚙ 行政管理</b><span>名冊、課表與借用管理</span></div></div></div>''',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="login"><div class="login-title">系統登入 / System Login</div><div class="rule"></div>',unsafe_allow_html=True)
        with st.form('login'):
            role=st.radio('身分 / Role',['教師','學生','管理員'],horizontal=True);admin=role=='管理員';cred=st.text_input('管理員密碼' if admin else '教師職編／學生學號',type='password' if admin else 'default');remember=st.checkbox('記住我的帳號 / Remember me');ok=st.form_submit_button('登入 Login',use_container_width=True)
        a,b=st.columns(2);a.caption('🔒 忘記密碼？');b.caption('☎ 聯絡系辦')
        if ok:
            if not cred.strip():st.error('請輸入登入資料。')
            elif admin:
                if cred==admin_password():st.session_state.user={'user_type':'管理員','name':'Administrator','identification_code':'ADMIN','email':''};st.session_state.admin=True;st.rerun()
                else:st.error('管理員密碼錯誤。')
            else:
                u=verify_authorized_user_by_code(role,cred)
                if u:st.session_state.user=u;st.session_state.admin=False;st.rerun()
                else:st.error('身分驗證失敗，僅限心理學系教師及學生使用。')
        st.caption('本系統僅供亞洲大學心理學系教師與學生使用。');st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('''<div class="quick-grid"><div class="quick"><b>▦ 教室課表</b><p>查看課表與使用狀況</p></div><div class="quick"><b>◉ 系統公告</b><p>重要通知與公告</p></div><div class="quick"><b>▤ 使用說明</b><p>操作手冊與指南</p></div><div class="quick"><b>▥ 最新消息</b><p>系統更新資訊</p></div></div><div class="footer-note">AU-PCRS V8.0 Professional UI Edition ｜ © 2026 亞洲大學心理學系</div>''',unsafe_allow_html=True)
def home():
    st.markdown('## 智慧儀表板 / Dashboard');c=get_dashboard_counts();a,b,d,e=st.columns(4);a.metric('教師 Faculty',c['teachers']);b.metric('學生 Students',c['students']);d.metric('有效借用 Active',c['active_bookings']);e.metric('專業教室 Rooms',len(ROOMS));p=get_active_open_period();st.success(f"目前開放：{p['semester']}｜{p['start_date']}～{p['end_date']}") if p else st.warning('尚未設定開放借用期間');ok,msg=database_health_check();st.info(f'✅ Database：{msg}') if ok else st.error(msg)
def reserve():
    u=st.session_state.user;st.markdown('## 我要借教室 / Reserve');st.info(f"登入者：{u['name']}（{u['user_type']}）")
    with st.form('booking'):
        l,r=st.columns(2)
        with l:bd=st.date_input('借用日期',value=date.today(),min_value=date.today());room=st.selectbox('教室',ROOMS);start=st.selectbox('開始時間',[x for x,_ in SLOTS]);end=st.selectbox('結束時間',[x for _,x in SLOTS])
        with r:phone=st.text_input('聯絡手機');email=st.text_input('聯絡信箱',value=u.get('email') or '');reason=st.text_area('借用事由',height=160)
        go=st.form_submit_button('送出申請',use_container_width=True)
    if go:
        if not phone.strip() or not email.strip() or not reason.strip():st.error('請完整填寫必填欄位。');return
        if not valid_phone(phone) or not valid_email(email) or start>=end:st.error('輸入格式不正確。');return
        p=get_active_open_period()
        if not p or not(str(p['start_date'])<=str(bd)<=str(p['end_date'])):st.error('所選日期不在開放期間。');return
        cf=check_booking_conflict(str(bd),room,start,end)
        if cf:st.error(f"時段衝突：{cf['detail']}");return
        bid=create_booking(str(bd),room,start,end,u['user_type'],u['name'],u['identification_code'],phone,email,reason);st.success(f'申請完成，借用編號：{bid}')
def query():
    st.markdown('## 教室查詢 / Availability');a,b=st.columns(2)
    with a:qd=st.date_input('日期',value=date.today(),key='qd')
    with b:qr=st.selectbox('教室',ROOMS,key='qr')
    cs=get_course_blocks(str(qd),qr);bs=[x for x in get_all_bookings() if str(x['booking_date'])==str(qd) and x['room']==qr and x['status']=='有效'];out=[]
    for s,e in SLOTS:
        status,detail='可借用',''
        for c in cs:
            if s<str(c['end_time'])[:5] and e>str(c['start_time'])[:5]:status,detail='已排課',c['course_name'];break
        if status=='可借用':
            for x in bs:
                if s<str(x['end_time'])[:5] and e>str(x['start_time'])[:5]:status,detail='已借用',x['reason'];break
        out.append({'時間':f'{s}–{e}','狀態':status,'說明':detail})
    st.dataframe(pd.DataFrame(out),use_container_width=True,hide_index=True)
def admin_page():
    st.markdown('## 管理員後台');tabs=st.tabs(['儀表板','名冊管理','開放期間','課表管理','借用管理','操作紀錄'])
    with tabs[0]:home()
    with tabs[1]:
        typ=st.radio('名冊類別',['教師','學生'],horizontal=True);up=st.file_uploader('Excel：辨識碼、姓名、聯絡信箱、狀態',type=['xlsx'],key='roster');rep=st.checkbox('覆蓋此類名冊')
        if st.button('匯入名冊',use_container_width=True):
            if up is None:st.error('請先選擇檔案')
            else:
                try:st.success(import_authorized_users(pd.read_excel(up,dtype=str).fillna(''),typ,rep))
                except Exception as e:st.error(e)
        rows=get_all_authorized_users();st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True) if rows else None
    with tabs[2]:
        a,b=st.columns(2)
        with a:sd=st.date_input('開始日期',value=date.today())
        with b:ed=st.date_input('結束日期',value=date.today())
        sem=st.text_input('學期',value='115-1')
        if st.button('儲存並啟用',use_container_width=True):save_open_period(sem,str(sd),str(ed));st.success('已儲存')
    with tabs[3]:
        sem=st.text_input('匯入學期',value='115-1',key='sem');rep=st.checkbox('清除此學期既有課表');up=st.file_uploader('課表 Excel',type=['xlsx'],key='course')
        if up is not None:
            df=pd.read_excel(up,dtype=str).fillna('');st.dataframe(df.head(20),use_container_width=True,hide_index=True)
            if st.button('確認匯入課表',use_container_width=True):st.success(add_course_blocks(df,sem,rep))
        ss=get_course_semesters();st.dataframe(pd.DataFrame(ss),use_container_width=True,hide_index=True) if ss else None
    with tabs[4]:
        rows=get_all_bookings()
        if rows:
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True);st.download_button('匯出 Excel',xlsx(rows,'借用紀錄'),f'bookings_{date.today()}.xlsx',use_container_width=True);bid=st.selectbox('借用編號',[r['booking_id'] for r in rows]);reason=st.text_input('取消原因')
            if st.button('取消借用') and reason.strip():cancel_booking(bid,reason.strip());st.rerun()
        else:st.info('目前尚無借用紀錄')
    with tabs[5]:
        logs=get_audit_logs();st.dataframe(pd.DataFrame(logs),use_container_width=True,hide_index=True) if logs else st.info('目前尚無操作紀錄')

st.set_page_config(page_title='AU-PCRS V8.0',page_icon='🧠',layout='wide');style()
for k,v in {'language':'中文','user':None,'admin':False}.items():
    if k not in st.session_state:st.session_state[k]=v
try:init_db()
except Exception as e:st.error('資料庫初始化失敗');st.caption(str(e));st.stop()
if st.session_state.user is None:
    with st.sidebar:st.session_state.language=st.selectbox('語言 / Language',['中文','English']);st.caption('AU-PCRS V8.0 Professional UI Edition')
    login_page();st.stop()
with st.sidebar:
    if PSY_LOGO.exists():st.image(str(PSY_LOGO),width=110)
    st.markdown(f"### {st.session_state.user['name']}");st.caption(st.session_state.user['user_type']);t=TXT[st.session_state.language];pages=[t['home'],t['adminp']] if st.session_state.admin else [t['home'],t['reserve'],t['query']];page=st.radio('功能選單 / Menu',pages)
    if st.button(t['logout'],use_container_width=True):st.session_state.user=None;st.session_state.admin=False;st.rerun()
topbar()
if page==t['home']:home()
elif page==t['reserve']:reserve()
elif page==t['query']:query()
else:admin_page()
