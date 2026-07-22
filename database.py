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
    Column("updated_at", DateTime), Column("cancel_reason", Text), Column("cancelled_at", DateTime), Column("reviewed_by", String(100)), Column("reviewed_at", DateTime), Column("review_note", Text), Column("approval_mode", String(20)))
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

announcements = Table("system_announcements", metadata,
    Column("id", Integer, primary_key=True),
    Column("title_zh", String(255), nullable=False),
    Column("title_en", String(255)),
    Column("content_zh", Text, nullable=False),
    Column("content_en", Text),
    Column("category", String(50), nullable=False, default="一般公告"),
    Column("publish_start", Date),
    Column("publish_end", Date),
    Column("is_published", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, default=datetime.now),
    Column("updated_at", DateTime))

system_settings = Table("system_settings", metadata,
    Column("setting_key", String(100), primary_key=True),
    Column("setting_value", String(500), nullable=False),
    Column("updated_at", DateTime, default=datetime.now))

def _date(v): return v if isinstance(v, date) else date.fromisoformat(str(v))
def _time(v): return v if isinstance(v, time) else time.fromisoformat(str(v)[:5])

def as_date(value):
    """Normalize string/date/datetime values into a Python date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value).strip()
    if not text_value:
        raise ValueError("Date value cannot be empty.")
    return date.fromisoformat(text_value[:10])



def as_time(value):
    """Normalize string/time/datetime values into a Python time."""
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    text_value = str(value).strip()
    if not text_value:
        raise ValueError("Time value cannot be empty.")
    return time.fromisoformat(text_value[:5])


def _rows(r): return [dict(x._mapping) for x in r]
rows = _rows
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




def repair_announcement_id_sequence():
    """Repair PostgreSQL auto-numbering for system_announcements.id."""
    if engine.dialect.name != "postgresql":
        return True
    with engine.begin() as conn:
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS system_announcements_id_seq"))
        conn.execute(text("ALTER SEQUENCE system_announcements_id_seq OWNED BY system_announcements.id"))
        conn.execute(text(
            "ALTER TABLE system_announcements "
            "ALTER COLUMN id SET DEFAULT nextval('system_announcements_id_seq')"
        ))
        conn.execute(text(
            "SELECT setval("
            "'system_announcements_id_seq', "
            "COALESCE((SELECT MAX(id) FROM system_announcements), 0) + 1, false)"
        ))
    return True



def migrate_legacy_announcements():
    """
    Best-effort migration from older `announcements` table into the clean
    `system_announcements` table. It never blocks startup.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "announcements" not in tables or "system_announcements" not in tables:
        return 0

    legacy_columns = {col["name"] for col in inspector.get_columns("system_announcements")}
    required = {"title_zh", "content_zh"}
    if not required.issubset(legacy_columns):
        return 0

    select_columns = [
        "title_zh",
        "content_zh",
        "title_en" if "title_en" in legacy_columns else "NULL AS title_en",
        "content_en" if "content_en" in legacy_columns else "NULL AS content_en",
        "category" if "category" in legacy_columns else "'一般公告' AS category",
        "publish_start" if "publish_start" in legacy_columns else "NULL AS publish_start",
        "publish_end" if "publish_end" in legacy_columns else "NULL AS publish_end",
        "is_published" if "is_published" in legacy_columns else "TRUE AS is_published",
        "created_at" if "created_at" in legacy_columns else "CURRENT_TIMESTAMP AS created_at",
        "updated_at" if "updated_at" in legacy_columns else "NULL AS updated_at",
    ]

    try:
        with engine.begin() as conn:
            existing_count = conn.execute(
                text("SELECT COUNT(*) FROM system_announcements")
            ).scalar_one()
            if existing_count:
                return 0

            sql = (
                "INSERT INTO system_announcements "
                "(title_zh,title_en,content_zh,content_en,category,"
                "publish_start,publish_end,is_published,created_at,updated_at) "
                "SELECT " + ",".join(select_columns) + " FROM announcements"
            )
            result = conn.execute(text(sql))
            return result.rowcount or 0
    except Exception:
        return 0


def ensure_feature_tables():
    """
    Create and repair V9.3+ feature tables.

    create_all() creates missing tables but does not add missing columns to
    existing tables, so every required announcement/settings column is also
    checked explicitly.
    """
    metadata.create_all(engine)

    tables = set(inspect(engine).get_table_names())
    if "system_announcements" not in tables or "system_settings" not in tables:
        # Run the targeted create again with a fresh connection/inspection.
        metadata.create_all(
            engine,
            tables=[announcements, system_settings, audit_logs],
            checkfirst=True,
        )
        tables = set(inspect(engine).get_table_names())

    missing_tables = {"system_announcements", "system_settings"} - tables
    if missing_tables:
        raise RuntimeError(
            "Required tables could not be created: "
            + ", ".join(sorted(missing_tables))
        )

    announcement_columns = {
        "title_zh": "title_zh VARCHAR(255)",
        "title_en": "title_en VARCHAR(255)",
        "content_zh": "content_zh TEXT",
        "content_en": "content_en TEXT",
        "category": "category VARCHAR(50)",
        "publish_start": "publish_start DATE",
        "publish_end": "publish_end DATE",
        "is_published": "is_published BOOLEAN",
        "created_at": "created_at TIMESTAMP",
        "updated_at": "updated_at TIMESTAMP",
    }
    for column_name, ddl in announcement_columns.items():
        _add_column_if_missing("system_announcements", column_name, ddl)

    setting_columns = {
        "setting_value": "setting_value VARCHAR(500)",
        "updated_at": "updated_at TIMESTAMP",
    }
    for column_name, ddl in setting_columns.items():
        _add_column_if_missing("system_settings", column_name, ddl)

    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE system_announcements "
            "SET title_zh = '未命名公告' "
            "WHERE title_zh IS NULL OR TRIM(title_zh) = ''"
        ))
        conn.execute(text(
            "UPDATE system_announcements "
            "SET content_zh = '' "
            "WHERE content_zh IS NULL"
        ))
        conn.execute(text(
            "UPDATE system_announcements "
            "SET category = '一般公告' "
            "WHERE category IS NULL OR TRIM(category) = ''"
        ))
        conn.execute(text(
            "UPDATE system_announcements "
            "SET is_published = TRUE "
            "WHERE is_published IS NULL"
        ))
        conn.execute(text(
            "UPDATE system_announcements "
            "SET created_at = CURRENT_TIMESTAMP "
            "WHERE created_at IS NULL"
        ))

    repair_announcement_id_sequence()
    migrate_legacy_announcements()
    return True


def migrate_schema():
    """Upgrade older SQLite/Supabase schemas without deleting existing data."""
    ensure_feature_tables()
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
            ("reviewed_by", 'reviewed_by VARCHAR(100)'),
            ("reviewed_at", 'reviewed_at TIMESTAMP'),
            ("review_note", 'review_note TEXT'),
            ("approval_mode", 'approval_mode VARCHAR(20)'),
        ]:
            _add_column_if_missing("bookings", name, ddl)
        with engine.begin() as conn:
            conn.execute(text("UPDATE bookings SET status = '已核准' WHERE status = '有效'"))
            conn.execute(text("UPDATE bookings SET approval_mode = '歷史資料' WHERE approval_mode IS NULL AND status = '已核准'"))

    if "system_announcements" in tables:
        for name, ddl in [
            ("title_en", 'title_en VARCHAR(255)'),
            ("content_en", 'content_en TEXT'),
            ("category", "category VARCHAR(50)"),
            ("publish_start", 'publish_start DATE'),
            ("publish_end", 'publish_end DATE'),
            ("is_published", 'is_published BOOLEAN'),
            ("created_at", 'created_at TIMESTAMP'),
            ("updated_at", 'updated_at TIMESTAMP'),
        ]:
            _add_column_if_missing("system_announcements", name, ddl)
        with engine.begin() as conn:
            conn.execute(text("UPDATE system_announcements SET category = '一般公告' WHERE category IS NULL OR TRIM(category) = ''"))
            conn.execute(text("UPDATE system_announcements SET is_published = TRUE WHERE is_published IS NULL"))
            conn.execute(text("UPDATE system_announcements SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))


def init_db():
    metadata.create_all(engine)
    ensure_feature_tables()
    migrate_schema()
    return True

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
    cond=[bookings.c.booking_date==_date(booking_date),bookings.c.room==room,bookings.c.status.in_(["待審核","已核准"]),s<bookings.c.end_time,e>bookings.c.start_time]
    if exclude_booking_id:cond.append(bookings.c.booking_id!=exclude_booking_id)
    with engine.connect() as c:r=c.execute(select(bookings.c.booking_id).where(and_(*cond)).limit(1)).first()
    return {"type":"booking","detail":r._mapping["booking_id"]} if r else None
def create_booking(booking_date, room, start_time, end_time, applicant_type,
                   applicant_name, identification_code, phone, email, reason):
    auto_approve = get_setting_bool("auto_approve_bookings", False)
    booking_status = "已核准" if auto_approve else "待審核"
    approval_mode = "自動核准" if auto_approve else "人工審核"
    reviewed_by = "SYSTEM" if auto_approve else None
    reviewed_at = datetime.now() if auto_approve else None
    with engine.begin() as c:
        r = c.execute(insert(bookings).values(
            booking_id=None,
            booking_date=_date(booking_date),
            room=room,
            start_time=_time(start_time),
            end_time=_time(end_time),
            applicant_type=applicant_type,
            applicant_name=applicant_name,
            identification_code=identification_code,
            phone=phone,
            email=email,
            reason=reason,
            status=booking_status,
            approval_mode=approval_mode,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            created_at=datetime.now(),
        ))
        rid = int(r.inserted_primary_key[0])
        bid = f"AU-PSY-{_date(booking_date).strftime('%Y%m%d')}-{rid:05d}"
        c.execute(update(bookings).where(bookings.c.id == rid).values(booking_id=bid))
    log_action("CREATE", "booking", bid, f"{room} {start_time}-{end_time} status={booking_status}")
    return bid, booking_status

def get_bookings_by_date_room(booking_date, room, status=None):
    """Return only bookings required by the classroom availability page."""
    conditions = [
        bookings.c.booking_date == as_date(booking_date),
        bookings.c.room == room,
    ]
    if status:
        conditions.append(bookings.c.status == status)
    else:
        conditions.append(bookings.c.status.in_(["待審核", "已核准"]))

    stmt = (
        select(bookings)
        .where(and_(*conditions))
        .order_by(bookings.c.start_time)
    )
    with engine.connect() as conn:
        return rows(conn.execute(stmt))


def get_recent_bookings(limit=300):
    """Return a bounded list for the administration screen."""
    safe_limit = max(1, min(int(limit), 2000))
    stmt = (
        select(bookings)
        .order_by(bookings.c.booking_date.desc(), bookings.c.start_time.desc())
        .limit(safe_limit)
    )
    with engine.connect() as conn:
        return rows(conn.execute(stmt))


def get_room_status_counts(booking_date, room):
    """Small helper for dashboard/public schedule without loading all bookings."""
    stmt = select(func.count()).select_from(bookings).where(and_(
        bookings.c.booking_date == as_date(booking_date),
        bookings.c.room == room,
        bookings.c.status.in_(["待審核", "已核准"]),
    ))
    with engine.connect() as conn:
        return int(conn.execute(stmt).scalar_one())


def get_all_bookings():
    with engine.connect() as c:return _rows(c.execute(select(bookings).order_by(bookings.c.booking_date.desc(),bookings.c.start_time.desc())))
def get_booking_by_id(booking_id):
    with engine.connect() as c:r=c.execute(select(bookings).where(bookings.c.booking_id==booking_id)).first()
    return dict(r._mapping) if r else None
def update_booking(booking_id,booking_date,room,start_time,end_time,reason):
    with engine.begin() as c:c.execute(update(bookings).where(and_(bookings.c.booking_id==booking_id,bookings.c.status.in_(["待審核","已核准"]))).values(booking_date=_date(booking_date),room=room,start_time=_time(start_time),end_time=_time(end_time),reason=reason,updated_at=datetime.now()))
def cancel_booking(booking_id,cancel_reason):
    with engine.begin() as c:c.execute(update(bookings).where(and_(bookings.c.booking_id==booking_id,bookings.c.status.in_(["待審核","已核准"]))).values(status="已取消",cancel_reason=cancel_reason,cancelled_at=datetime.now()))
def get_dashboard_counts():
    with engine.connect() as c:
        t=c.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type=="教師",authorized_users.c.status=="啟用"))).scalar_one(); s=c.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type=="學生",authorized_users.c.status=="啟用"))).scalar_one(); a=c.execute(select(func.count()).select_from(bookings).where(bookings.c.status.in_(["待審核","已核准"]))).scalar_one()
    return {"teachers":t,"students":s,"active_bookings":a}
def get_audit_logs(limit=1000):
    with engine.connect() as c:return _rows(c.execute(select(audit_logs).order_by(audit_logs.c.id.desc()).limit(max(1,min(int(limit),5000)))))



def get_setting(setting_key, default=None):
    ensure_feature_tables()
    with engine.connect() as conn:
        row = conn.execute(
            select(system_settings.c.setting_value).where(
                system_settings.c.setting_key == setting_key
            )
        ).first()
    return row[0] if row else default


def set_setting(setting_key, setting_value):
    ensure_feature_tables()
    value = str(setting_value)
    with engine.begin() as conn:
        exists = conn.execute(
            select(system_settings.c.setting_key).where(
                system_settings.c.setting_key == setting_key
            )
        ).first()
        if exists:
            conn.execute(
                update(system_settings)
                .where(system_settings.c.setting_key == setting_key)
                .values(setting_value=value, updated_at=datetime.now())
            )
        else:
            conn.execute(
                insert(system_settings).values(
                    setting_key=setting_key,
                    setting_value=value,
                    updated_at=datetime.now(),
                )
            )
    log_action("SETTING", "system_settings", setting_key, value)


def get_setting_bool(setting_key, default=False):
    value = get_setting(setting_key, None)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "啟用"}


def create_announcement(title_zh, content_zh, title_en="", content_en="",
                        category="一般公告", publish_start=None, publish_end=None,
                        is_published=True):
    ensure_feature_tables()
    values = dict(
        title_zh=title_zh.strip(),
        title_en=title_en.strip(),
        content_zh=content_zh.strip(),
        content_en=content_en.strip(),
        category=category,
        publish_start=as_date(publish_start) if publish_start else None,
        publish_end=as_date(publish_end) if publish_end else None,
        is_published=bool(is_published),
        created_at=datetime.now(),
    )
    try:
        with engine.begin() as conn:
            result = conn.execute(insert(announcements).values(**values))
            announcement_id = int(result.inserted_primary_key[0])
    except IntegrityError:
        repair_announcement_id_sequence()
        with engine.begin() as conn:
            result = conn.execute(insert(announcements).values(**values))
            announcement_id = int(result.inserted_primary_key[0])
    log_action("CREATE", "announcement", str(announcement_id), title_zh)
    return announcement_id

def update_announcement(announcement_id, title_zh, content_zh, title_en="",
                        content_en="", category="一般公告", publish_start=None,
                        publish_end=None, is_published=True):
    ensure_feature_tables()
    with engine.begin() as conn:
        conn.execute(
            update(announcements)
            .where(announcements.c.id == int(announcement_id))
            .values(
                title_zh=title_zh.strip(),
                title_en=title_en.strip(),
                content_zh=content_zh.strip(),
                content_en=content_en.strip(),
                category=category,
                publish_start=as_date(publish_start) if publish_start else None,
                publish_end=as_date(publish_end) if publish_end else None,
                is_published=bool(is_published),
                updated_at=datetime.now(),
            )
        )
    log_action("UPDATE", "announcement", str(announcement_id), title_zh)


def delete_announcement(announcement_id):
    ensure_feature_tables()
    with engine.begin() as conn:
        conn.execute(delete(announcements).where(announcements.c.id == int(announcement_id)))
    log_action("DELETE", "announcement", str(announcement_id), "")


def get_all_announcements():
    stmt = select(announcements).order_by(
        announcements.c.created_at.desc(),
        announcements.c.id.desc(),
    )
    try:
        ensure_feature_tables()
        with engine.connect() as conn:
            return _rows(conn.execute(stmt))
    except Exception:
        # Repair all feature objects and retry once.
        metadata.create_all(engine)
        ensure_feature_tables()
        with engine.connect() as conn:
            return _rows(conn.execute(stmt))

def get_active_announcements(reference_date=None):
    current = as_date(reference_date or date.today())
    conditions = [
        announcements.c.is_published.is_(True),
        (
            announcements.c.publish_start.is_(None)
            | (announcements.c.publish_start <= current)
        ),
        (
            announcements.c.publish_end.is_(None)
            | (announcements.c.publish_end >= current)
        ),
    ]
    stmt = (
        select(announcements)
        .where(and_(*conditions))
        .order_by(announcements.c.created_at.desc(), announcements.c.id.desc())
    )
    try:
        ensure_feature_tables()
        with engine.connect() as conn:
            return _rows(conn.execute(stmt))
    except Exception:
        metadata.create_all(engine)
        ensure_feature_tables()
        with engine.connect() as conn:
            return _rows(conn.execute(stmt))

def review_booking(booking_id, decision, reviewer="Administrator", note=""):
    if decision not in {"已核准", "已退回"}:
        raise ValueError("Invalid review decision.")
    with engine.begin() as conn:
        result = conn.execute(
            update(bookings)
            .where(and_(
                bookings.c.booking_id == booking_id,
                bookings.c.status == "待審核",
            ))
            .values(
                status=decision,
                reviewed_by=reviewer,
                reviewed_at=datetime.now(),
                review_note=note.strip(),
                approval_mode="人工審核",
                updated_at=datetime.now(),
            )
        )
    if not result.rowcount:
        raise ValueError("This reservation is no longer pending review.")
    log_action("REVIEW", "booking", booking_id, f"{decision}: {note}")
    return decision


def get_pending_bookings(limit=500):
    safe_limit = max(1, min(int(limit), 2000))
    with engine.connect() as conn:
        return _rows(conn.execute(
            select(bookings)
            .where(bookings.c.status == "待審核")
            .order_by(bookings.c.created_at.asc())
            .limit(safe_limit)
        ))


def initialize_database_once():
    """Initialize all base and feature schemas once per Streamlit process."""
    metadata.create_all(engine)
    ensure_feature_tables()
    migrate_schema()
    return True

