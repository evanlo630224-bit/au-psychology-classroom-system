from __future__ import annotations
from datetime import date, datetime, time
import os
from pathlib import Path
from typing import Any
import pandas as pd
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, MetaData, String, Table, Text, Time, UniqueConstraint, and_, create_engine, delete, func, insert, inspect, select, text, update
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).parent

def get_database_url():
    try:
        import streamlit as st
        if "database" in st.secrets:
            cfg = st.secrets["database"]
            req = {"host","port","name","user","password"}
            if req.issubset(cfg.keys()):
                return URL.create("postgresql+psycopg", username=str(cfg["user"]), password=str(cfg["password"]), host=str(cfg["host"]), port=int(cfg["port"]), database=str(cfg["name"]), query={"sslmode":"require"})
        if "DATABASE_URL" in st.secrets:
            return str(st.secrets["DATABASE_URL"])
    except Exception:
        pass
    return os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR/'classroom_booking.db'}"

url = get_database_url()
if isinstance(url, str):
    url = url.replace("postgres://", "postgresql+psycopg://", 1) if url.startswith("postgres://") else url
    url = url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url
kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
if str(url).startswith("postgresql+psycopg://"):
    kwargs.update({"poolclass": NullPool, "connect_args": {"connect_timeout": 12}})
engine: Engine = create_engine(url, **kwargs)
metadata = MetaData()

authorized_users = Table("authorized_users", metadata,
    Column("id", Integer, primary_key=True), Column("user_type", String(20), nullable=False),
    Column("identification_code", String(100), nullable=False), Column("name", String(100), nullable=False),
    Column("email", String(255)), Column("status", String(20), nullable=False, default="啟用"),
    Column("imported_at", DateTime, nullable=False, default=datetime.now),
    UniqueConstraint("user_type","identification_code", name="uq_authorized_user"))
bookings = Table("bookings", metadata,
    Column("id", Integer, primary_key=True), Column("booking_id", String(100), unique=True),
    Column("booking_date", Date, nullable=False), Column("room", String(30), nullable=False),
    Column("start_time", Time, nullable=False), Column("end_time", Time, nullable=False),
    Column("applicant_type", String(20), nullable=False), Column("applicant_name", String(100), nullable=False),
    Column("identification_code", String(100), nullable=False), Column("phone", String(50), nullable=False),
    Column("email", String(255), nullable=False), Column("reason", Text, nullable=False),
    Column("status", String(20), nullable=False, default="有效"), Column("created_at", DateTime, default=datetime.now),
    Column("updated_at", DateTime), Column("cancel_reason", Text), Column("cancelled_at", DateTime))
open_periods = Table("open_periods", metadata,
    Column("id", Integer, primary_key=True), Column("semester", String(30), nullable=False),
    Column("start_date", Date, nullable=False), Column("end_date", Date, nullable=False),
    Column("is_active", Boolean, default=True), Column("created_at", DateTime, default=datetime.now))
course_blocks = Table("course_blocks", metadata,
    Column("id", Integer, primary_key=True), Column("semester", String(30), nullable=False),
    Column("room", String(30), nullable=False), Column("weekday", Integer, nullable=False),
    Column("start_time", Time, nullable=False), Column("end_time", Time, nullable=False),
    Column("course_name", String(255), nullable=False), Column("teacher", String(100)),
    Column("is_active", Boolean, default=True), Column("created_at", DateTime, default=datetime.now),
    UniqueConstraint("semester","room","weekday","start_time","end_time","course_name", name="uq_course_block"))
audit_logs = Table("audit_logs", metadata,
    Column("id", Integer, primary_key=True), Column("action", String(50), nullable=False),
    Column("target_type", String(50), nullable=False), Column("target_id", String(100)),
    Column("detail", Text), Column("created_at", DateTime, default=datetime.now))

def _date(v): return v if isinstance(v, date) else date.fromisoformat(str(v))
def _time(v): return v if isinstance(v, time) else time.fromisoformat(str(v)[:5])
def _rows(r): return [dict(x._mapping) for x in r]
def _column_names(table_name):
    try:
        return {col["name"] for col in inspect(engine).get_columns(table_name)}
    except Exception:
        return set()


def _add_column_if_missing(table_name, column_name, ddl):
    columns = _column_names(table_name)
    if column_name in columns:
        return False
    with engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {ddl}'))
    return True


def migrate_schema():
    """Upgrade older SQLite/Supabase schemas without deleting existing data."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "course_blocks" in tables:
        _add_column_if_missing("course_blocks", "semester", 'semester VARCHAR(30)')
        _add_column_if_missing("course_blocks", "is_active", 'is_active BOOLEAN')
        _add_column_if_missing("course_blocks", "created_at", 'created_at TIMESTAMP')
        with engine.begin() as conn:
            conn.execute(text("UPDATE course_blocks SET semester = '歷史課表' WHERE semester IS NULL OR TRIM(semester) = ''"))
            conn.execute(text("UPDATE course_blocks SET is_active = TRUE WHERE is_active IS NULL"))
            conn.execute(text("UPDATE course_blocks SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))

    if "open_periods" in tables:
        _add_column_if_missing("open_periods", "semester", 'semester VARCHAR(30)')
        _add_column_if_missing("open_periods", "is_active", 'is_active BOOLEAN')
        _add_column_if_missing("open_periods", "created_at", 'created_at TIMESTAMP')
        with engine.begin() as conn:
            conn.execute(text("UPDATE open_periods SET semester = '未設定' WHERE semester IS NULL OR TRIM(semester) = ''"))
            conn.execute(text("UPDATE open_periods SET is_active = TRUE WHERE is_active IS NULL"))
            conn.execute(text("UPDATE open_periods SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))

    if "authorized_users" in tables:
        _add_column_if_missing("authorized_users", "email", 'email VARCHAR(255)')
        _add_column_if_missing("authorized_users", "status", 'status VARCHAR(20)')
        _add_column_if_missing("authorized_users", "imported_at", 'imported_at TIMESTAMP')
        with engine.begin() as conn:
            conn.execute(text("UPDATE authorized_users SET status = '啟用' WHERE status IS NULL OR TRIM(status) = ''"))
            conn.execute(text("UPDATE authorized_users SET imported_at = CURRENT_TIMESTAMP WHERE imported_at IS NULL"))

    if "bookings" in tables:
        for name, ddl in [
            ("updated_at", 'updated_at TIMESTAMP'),
            ("cancel_reason", 'cancel_reason TEXT'),
            ("cancelled_at", 'cancelled_at TIMESTAMP'),
        ]:
            _add_column_if_missing("bookings", name, ddl)


def init_db():
    metadata.create_all(engine)
    migrate_schema()
def database_health_check():
    try:
        with engine.connect() as c: c.execute(text("SELECT 1"))
        return True, engine.dialect.name
    except Exception as e: return False, str(e)
def log_action(action,target_type,target_id="",detail=""):
    with engine.begin() as c: c.execute(insert(audit_logs).values(action=action,target_type=target_type,target_id=target_id,detail=detail,created_at=datetime.now()))
def verify_authorized_user_by_code(user_type, code):
    with engine.connect() as c:
        r=c.execute(select(authorized_users).where(and_(authorized_users.c.user_type==user_type,authorized_users.c.identification_code==code.strip(),authorized_users.c.status=="啟用"))).first()
    return dict(r._mapping) if r else None
def import_authorized_users(df:pd.DataFrame,user_type:str,replace:bool):
    req={"辨識碼","姓名","聯絡信箱","狀態"}; missing=req-set(df.columns)
    if missing: raise ValueError("Excel 缺少欄位："+"、".join(sorted(missing)))
    ins=upd=skip=0; w=df.fillna("")
    with engine.begin() as c:
        if replace: c.execute(delete(authorized_users).where(authorized_users.c.user_type==user_type))
        for _,r in w.iterrows():
            code,name=str(r["辨識碼"]).strip(),str(r["姓名"]).strip()
            if not code or not name: skip+=1; continue
            status=str(r["狀態"]).strip() if str(r["狀態"]).strip() in {"啟用","停用"} else "啟用"
            exists=c.execute(select(authorized_users.c.id).where(and_(authorized_users.c.user_type==user_type,authorized_users.c.identification_code==code))).first()
            vals=dict(name=name,email=str(r["聯絡信箱"]).strip(),status=status,imported_at=datetime.now())
            if exists: c.execute(update(authorized_users).where(and_(authorized_users.c.user_type==user_type,authorized_users.c.identification_code==code)).values(**vals)); upd+=1
            else: c.execute(insert(authorized_users).values(user_type=user_type,identification_code=code,**vals)); ins+=1
    log_action("IMPORT","authorized_users",user_type,f"新增{ins} 更新{upd}")
    return {"inserted":ins,"updated":upd,"skipped":skip}
def get_all_authorized_users():
    with engine.connect() as c:return _rows(c.execute(select(authorized_users).order_by(authorized_users.c.user_type,authorized_users.c.identification_code)))
def save_open_period(semester,start_date,end_date):
    with engine.begin() as c:
        c.execute(update(open_periods).values(is_active=False)); c.execute(insert(open_periods).values(semester=semester,start_date=_date(start_date),end_date=_date(end_date),is_active=True,created_at=datetime.now()))
def get_active_open_period():
    with engine.connect() as c:r=c.execute(select(open_periods).where(open_periods.c.is_active.is_(True)).order_by(open_periods.c.id.desc()).limit(1)).first()
    return dict(r._mapping) if r else None
def add_course_blocks(df,semester,replace=False):
    req={"教室","星期","開始時間","結束時間","課程名稱","教師"}; missing=req-set(df.columns)
    if missing: raise ValueError("Excel 缺少欄位："+"、".join(sorted(missing)))
    wm={"週一":0,"星期一":0,"週二":1,"星期二":1,"週三":2,"星期三":2,"週四":3,"星期四":3,"週五":4,"星期五":4,"週六":5,"星期六":5,"週日":6,"星期日":6}; ins=dup=skip=0
    if replace:
        with engine.begin() as c:c.execute(delete(course_blocks).where(course_blocks.c.semester==semester))
    for _,r in df.fillna("").iterrows():
        wd=wm.get(str(r["星期"]).strip()); room,start,end,name,teacher=[str(r[x]).strip() for x in ["教室","開始時間","結束時間","課程名稱","教師"]]
        if wd is None or not room or not start or not end or not name or start[:5]>=end[:5]: skip+=1; continue
        try:
            with engine.begin() as c:c.execute(insert(course_blocks).values(semester=semester,room=room,weekday=wd,start_time=_time(start),end_time=_time(end),course_name=name,teacher=teacher,is_active=True,created_at=datetime.now()))
            ins+=1
        except IntegrityError: dup+=1
    return {"inserted":ins,"duplicates":dup,"skipped":skip}
def get_course_semesters():
    """
    Return one summary row per semester.

    PostgreSQL does not support MAX(boolean), so use BOOL_OR(is_active).
    SQLite uses MAX(CAST(is_active AS INTEGER)).
    A final Python aggregation fallback keeps the admin page available even
    when an older database has unusual column types.
    """
    migrate_schema()

    if engine.dialect.name == "postgresql":
        active_aggregate = func.bool_or(course_blocks.c.is_active).label("is_active")
    else:
        from sqlalchemy import cast
        active_aggregate = func.max(
            cast(course_blocks.c.is_active, Integer)
        ).label("is_active")

    stmt = (
        select(
            course_blocks.c.semester,
            func.count().label("course_count"),
            active_aggregate,
        )
        .group_by(course_blocks.c.semester)
        .order_by(course_blocks.c.semester.desc())
    )

    try:
        with engine.connect() as conn:
            result = _rows(conn.execute(stmt))
        for row in result:
            row["is_active"] = bool(row.get("is_active"))
        return result
    except Exception:
        # Compatibility fallback: select raw rows and aggregate in Python.
        columns = _column_names("course_blocks")
        if "semester" not in columns:
            return []

        selected = [course_blocks.c.semester]
        if "is_active" in columns:
            selected.append(course_blocks.c.is_active)

        with engine.connect() as conn:
            raw = _rows(conn.execute(select(*selected)))

        grouped = {}
        for row in raw:
            semester = row.get("semester") or "歷史課表"
            item = grouped.setdefault(
                semester,
                {"semester": semester, "course_count": 0, "is_active": False},
            )
            item["course_count"] += 1
            if "is_active" not in row or row.get("is_active") is None:
                item["is_active"] = True
            else:
                item["is_active"] = item["is_active"] or bool(row.get("is_active"))

        return sorted(grouped.values(), key=lambda x: x["semester"], reverse=True)
def set_course_semester_active(semester,active):
    with engine.begin() as c:c.execute(update(course_blocks).where(course_blocks.c.semester==semester).values(is_active=bool(active)))
def delete_course_semester(semester):
    with engine.begin() as c:r=c.execute(delete(course_blocks).where(course_blocks.c.semester==semester))
    return r.rowcount or 0
def get_course_blocks(booking_date,room,semester=None):
    d=_date(booking_date)
    if semester is None:
        p=get_active_open_period(); semester=p["semester"] if p else None
    cond=[course_blocks.c.room==room,course_blocks.c.weekday==d.weekday(),course_blocks.c.is_active.is_(True)]
    if semester:cond.append(course_blocks.c.semester==semester)
    with engine.connect() as c:return _rows(c.execute(select(course_blocks).where(and_(*cond)).order_by(course_blocks.c.start_time)))
def check_booking_conflict(booking_date,room,start_time,end_time,exclude_booking_id=None):
    s,e=_time(start_time),_time(end_time)
    for x in get_course_blocks(booking_date,room):
        if s<x["end_time"] and e>x["start_time"]:return {"type":"course","detail":x["course_name"]}
    cond=[bookings.c.booking_date==_date(booking_date),bookings.c.room==room,bookings.c.status=="有效",s<bookings.c.end_time,e>bookings.c.start_time]
    if exclude_booking_id:cond.append(bookings.c.booking_id!=exclude_booking_id)
    with engine.connect() as c:r=c.execute(select(bookings.c.booking_id).where(and_(*cond)).limit(1)).first()
    return {"type":"booking","detail":r._mapping["booking_id"]} if r else None
def create_booking(booking_date,room,start_time,end_time,applicant_type,applicant_name,identification_code,phone,email,reason):
    with engine.begin() as c:
        r=c.execute(insert(bookings).values(booking_id=None,booking_date=_date(booking_date),room=room,start_time=_time(start_time),end_time=_time(end_time),applicant_type=applicant_type,applicant_name=applicant_name,identification_code=identification_code,phone=phone,email=email,reason=reason,status="有效",created_at=datetime.now()))
        rid=int(r.inserted_primary_key[0]); bid=f"AU-PSY-{_date(booking_date).strftime('%Y%m%d')}-{rid:05d}"; c.execute(update(bookings).where(bookings.c.id==rid).values(booking_id=bid))
    log_action("CREATE","booking",bid,f"{room} {start_time}-{end_time}"); return bid
def get_all_bookings():
    with engine.connect() as c:return _rows(c.execute(select(bookings).order_by(bookings.c.booking_date.desc(),bookings.c.start_time.desc())))
def get_booking_by_id(booking_id):
    with engine.connect() as c:r=c.execute(select(bookings).where(bookings.c.booking_id==booking_id)).first()
    return dict(r._mapping) if r else None
def update_booking(booking_id,booking_date,room,start_time,end_time,reason):
    with engine.begin() as c:c.execute(update(bookings).where(and_(bookings.c.booking_id==booking_id,bookings.c.status=="有效")).values(booking_date=_date(booking_date),room=room,start_time=_time(start_time),end_time=_time(end_time),reason=reason,updated_at=datetime.now()))
def cancel_booking(booking_id,cancel_reason):
    with engine.begin() as c:c.execute(update(bookings).where(and_(bookings.c.booking_id==booking_id,bookings.c.status=="有效")).values(status="已取消",cancel_reason=cancel_reason,cancelled_at=datetime.now()))
def get_dashboard_counts():
    with engine.connect() as c:
        t=c.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type=="教師",authorized_users.c.status=="啟用"))).scalar_one(); s=c.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type=="學生",authorized_users.c.status=="啟用"))).scalar_one(); a=c.execute(select(func.count()).select_from(bookings).where(bookings.c.status=="有效")).scalar_one()
    return {"teachers":t,"students":s,"active_bookings":a}
def get_audit_logs(limit=1000):
    with engine.connect() as c:return _rows(c.execute(select(audit_logs).order_by(audit_logs.c.id.desc()).limit(max(1,min(int(limit),5000)))))
