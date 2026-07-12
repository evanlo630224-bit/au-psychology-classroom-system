from __future__ import annotations
from datetime import date, datetime, time
import os
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, MetaData, String, Table, Text,
    Time, UniqueConstraint, and_, create_engine, delete, func, insert,
    select, text, update
)
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).parent


def get_database_url():
    """Build a safe SQLAlchemy URL from Streamlit Secrets.

    Preferred cloud format:
      [database]
      host = "aws-0-ap-northeast-1.pooler.supabase.com"
      port = 5432
      name = "postgres"
      user = "postgres.PROJECT_REF"
      password = "..."

    URL.create() safely handles special characters in passwords.
    """
    try:
        import streamlit as st

        if "database" in st.secrets:
            cfg = st.secrets["database"]
            required = {"host", "port", "name", "user", "password"}
            if required.issubset(set(cfg.keys())):
                return URL.create(
                    drivername="postgresql+psycopg",
                    username=str(cfg["user"]),
                    password=str(cfg["password"]),
                    host=str(cfg["host"]),
                    port=int(cfg["port"]),
                    database=str(cfg["name"]),
                    query={"sslmode": "require"},
                )

        if "DATABASE_URL" in st.secrets:
            value = str(st.secrets["DATABASE_URL"]).strip()
            if value:
                return value
    except Exception:
        pass

    env_value = os.getenv("DATABASE_URL", "").strip()
    if env_value:
        return env_value

    return f"sqlite:///{BASE_DIR / 'classroom_booking.db'}"


def normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

DATABASE_URL = get_database_url()
if isinstance(DATABASE_URL, str):
    DATABASE_URL = normalize_url(DATABASE_URL)
kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
if str(DATABASE_URL).startswith("postgresql+psycopg://"):
    kwargs.update({"poolclass": NullPool, "connect_args": {"connect_timeout": 12}})
engine: Engine = create_engine(DATABASE_URL, **kwargs)
metadata = MetaData()

authorized_users = Table(
    "authorized_users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_type", String(20), nullable=False),
    Column("identification_code", String(100), nullable=False),
    Column("name", String(100), nullable=False),
    Column("email", String(255)),
    Column("status", String(20), nullable=False, default="啟用"),
    Column("imported_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    UniqueConstraint("user_type", "identification_code", name="uq_authorized_user"),
)

bookings = Table(
    "bookings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("booking_id", String(100), unique=True),
    Column("booking_date", Date, nullable=False),
    Column("room", String(30), nullable=False),
    Column("start_time", Time, nullable=False),
    Column("end_time", Time, nullable=False),
    Column("applicant_type", String(20), nullable=False),
    Column("applicant_name", String(100), nullable=False),
    Column("identification_code", String(100), nullable=False),
    Column("phone", String(50), nullable=False),
    Column("email", String(255), nullable=False),
    Column("reason", Text, nullable=False),
    Column("status", String(20), nullable=False, default="有效"),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True)),
    Column("cancel_reason", Text),
    Column("cancelled_at", DateTime(timezone=True)),
)

open_periods = Table(
    "open_periods", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("semester", String(30), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
)

course_blocks = Table(
    "course_blocks", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("semester", String(30), nullable=False, default="未分類"),
    Column("room", String(30), nullable=False),
    Column("weekday", Integer, nullable=False),
    Column("start_time", Time, nullable=False),
    Column("end_time", Time, nullable=False),
    Column("course_name", String(255), nullable=False),
    Column("teacher", String(100)),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    UniqueConstraint("semester", "room", "weekday", "start_time", "end_time", "course_name", name="uq_course_block"),
)

audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", String(50), nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_id", String(100)),
    Column("detail", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
)


def as_date(v):
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def as_time(v):
    return v if isinstance(v, time) else time.fromisoformat(str(v)[:5])


def rows(result):
    return [dict(r._mapping) for r in result]


def init_db():
    metadata.create_all(engine)


def database_health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, engine.dialect.name
    except Exception as exc:
        return False, str(exc)


def log_action(action, target_type, target_id="", detail=""):
    with engine.begin() as conn:
        conn.execute(insert(audit_logs).values(action=action, target_type=target_type, target_id=target_id, detail=detail, created_at=datetime.now()))


def verify_authorized_user_by_code(user_type, code):
    stmt = select(authorized_users).where(and_(
        authorized_users.c.user_type == user_type.strip(),
        authorized_users.c.identification_code == code.strip(),
        authorized_users.c.status == "啟用",
    ))
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
    return dict(row._mapping) if row else None


def import_authorized_users(df: pd.DataFrame, user_type: str, replace: bool):
    required = {"辨識碼", "姓名", "聯絡信箱", "狀態"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Excel 缺少欄位：" + "、".join(sorted(missing)))
    work = df.copy().fillna("")
    for col in required:
        work[col] = work[col].astype(str).str.strip()
    inserted = updated = skipped = 0
    with engine.begin() as conn:
        if replace:
            conn.execute(delete(authorized_users).where(authorized_users.c.user_type == user_type))
        for _, r in work.iterrows():
            code, name = r["辨識碼"], r["姓名"]
            if not code or not name:
                skipped += 1; continue
            status = r["狀態"] if r["狀態"] in {"啟用", "停用"} else "啟用"
            exists = conn.execute(select(authorized_users.c.id).where(and_(authorized_users.c.user_type == user_type, authorized_users.c.identification_code == code))).first()
            values = dict(name=name, email=r["聯絡信箱"], status=status, imported_at=datetime.now())
            if exists:
                conn.execute(update(authorized_users).where(and_(authorized_users.c.user_type == user_type, authorized_users.c.identification_code == code)).values(**values)); updated += 1
            else:
                conn.execute(insert(authorized_users).values(user_type=user_type, identification_code=code, **values)); inserted += 1
    log_action("IMPORT", "authorized_users", user_type, f"新增{inserted} 更新{updated}")
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def get_all_authorized_users():
    stmt = select(authorized_users).order_by(authorized_users.c.user_type, authorized_users.c.identification_code)
    with engine.connect() as conn:
        return rows(conn.execute(stmt))


def save_open_period(semester, start_date, end_date):
    with engine.begin() as conn:
        conn.execute(update(open_periods).values(is_active=False))
        conn.execute(insert(open_periods).values(semester=semester, start_date=as_date(start_date), end_date=as_date(end_date), is_active=True, created_at=datetime.now()))


def get_active_open_period():
    stmt = select(open_periods).where(open_periods.c.is_active.is_(True)).order_by(open_periods.c.id.desc()).limit(1)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
    return dict(row._mapping) if row else None


def add_course_blocks(df: pd.DataFrame, semester: str, replace: bool=False):
    required = {"教室", "星期", "開始時間", "結束時間", "課程名稱", "教師"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Excel 缺少欄位：" + "、".join(sorted(missing)))
    wmap = {"週一":0,"星期一":0,"週二":1,"星期二":1,"週三":2,"星期三":2,"週四":3,"星期四":3,"週五":4,"星期五":4,"週六":5,"星期六":5,"週日":6,"星期日":6}
    inserted = duplicates = skipped = 0
    with engine.begin() as conn:
        if replace:
            conn.execute(delete(course_blocks).where(course_blocks.c.semester == semester))
        for _, r in df.fillna("").iterrows():
            wd = wmap.get(str(r["星期"]).strip())
            room, start, end, name, teacher = [str(r[c]).strip() for c in ["教室","開始時間","結束時間","課程名稱","教師"]]
            if wd is None or not room or not start or not end or not name or start[:5] >= end[:5]:
                skipped += 1; continue
            try:
                conn.execute(insert(course_blocks).values(semester=semester, room=room, weekday=wd, start_time=as_time(start), end_time=as_time(end), course_name=name, teacher=teacher, is_active=True, created_at=datetime.now())); inserted += 1
            except IntegrityError:
                duplicates += 1
    return {"inserted": inserted, "duplicates": duplicates, "skipped": skipped}


def get_course_semesters():
    stmt = select(course_blocks.c.semester, func.count().label("course_count"), func.max(course_blocks.c.is_active).label("is_active")).group_by(course_blocks.c.semester).order_by(course_blocks.c.semester.desc())
    with engine.connect() as conn:
        return rows(conn.execute(stmt))


def set_course_semester_active(semester, active):
    with engine.begin() as conn:
        conn.execute(update(course_blocks).where(course_blocks.c.semester == semester).values(is_active=bool(active)))


def delete_course_semester(semester):
    with engine.begin() as conn:
        result = conn.execute(delete(course_blocks).where(course_blocks.c.semester == semester))
        return result.rowcount or 0


def get_course_blocks(booking_date, room, semester=None):
    d = as_date(booking_date)
    if semester is None:
        p = get_active_open_period(); semester = p["semester"] if p else None
    cond = [course_blocks.c.room == room, course_blocks.c.weekday == d.weekday(), course_blocks.c.is_active.is_(True)]
    if semester:
        cond.append(course_blocks.c.semester == semester)
    with engine.connect() as conn:
        return rows(conn.execute(select(course_blocks).where(and_(*cond)).order_by(course_blocks.c.start_time)))


def check_booking_conflict(booking_date, room, start_time, end_time, exclude_booking_id=None):
    s, e = as_time(start_time), as_time(end_time)
    for c in get_course_blocks(booking_date, room):
        if s < c["end_time"] and e > c["start_time"]:
            return {"type":"course", "detail":c["course_name"]}
    cond = [bookings.c.booking_date == as_date(booking_date), bookings.c.room == room, bookings.c.status == "有效", s < bookings.c.end_time, e > bookings.c.start_time]
    if exclude_booking_id:
        cond.append(bookings.c.booking_id != exclude_booking_id)
    with engine.connect() as conn:
        row = conn.execute(select(bookings.c.booking_id).where(and_(*cond)).limit(1)).first()
    return {"type":"booking", "detail":row._mapping["booking_id"]} if row else None


def create_booking(booking_date, room, start_time, end_time, applicant_type, applicant_name, identification_code, phone, email, reason):
    with engine.begin() as conn:
        result = conn.execute(insert(bookings).values(booking_id=None, booking_date=as_date(booking_date), room=room, start_time=as_time(start_time), end_time=as_time(end_time), applicant_type=applicant_type, applicant_name=applicant_name, identification_code=identification_code, phone=phone, email=email, reason=reason, status="有效", created_at=datetime.now()))
        row_id = int(result.inserted_primary_key[0])
        bid = f"AU-PSY-{as_date(booking_date).strftime('%Y%m%d')}-{row_id:05d}"
        conn.execute(update(bookings).where(bookings.c.id == row_id).values(booking_id=bid))
    log_action("CREATE", "booking", bid, f"{room} {start_time}-{end_time}")
    return bid


def get_all_bookings():
    with engine.connect() as conn:
        return rows(conn.execute(select(bookings).order_by(bookings.c.booking_date.desc(), bookings.c.start_time.desc())))


def get_booking_by_id(booking_id):
    with engine.connect() as conn:
        row = conn.execute(select(bookings).where(bookings.c.booking_id == booking_id)).first()
    return dict(row._mapping) if row else None


def update_booking(booking_id, booking_date, room, start_time, end_time, reason):
    with engine.begin() as conn:
        conn.execute(update(bookings).where(and_(bookings.c.booking_id == booking_id, bookings.c.status == "有效")).values(booking_date=as_date(booking_date), room=room, start_time=as_time(start_time), end_time=as_time(end_time), reason=reason, updated_at=datetime.now()))


def cancel_booking(booking_id, cancel_reason):
    with engine.begin() as conn:
        conn.execute(update(bookings).where(and_(bookings.c.booking_id == booking_id, bookings.c.status == "有效")).values(status="已取消", cancel_reason=cancel_reason, cancelled_at=datetime.now()))


def get_dashboard_counts():
    with engine.connect() as conn:
        teachers = conn.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type == "教師", authorized_users.c.status == "啟用"))).scalar_one()
        students = conn.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type == "學生", authorized_users.c.status == "啟用"))).scalar_one()
        active = conn.execute(select(func.count()).select_from(bookings).where(bookings.c.status == "有效")).scalar_one()
    return {"teachers": teachers, "students": students, "active_bookings": active}


def get_audit_logs(limit=1000):
    with engine.connect() as conn:
        return rows(conn.execute(select(audit_logs).order_by(audit_logs.c.id.desc()).limit(max(1, min(int(limit), 5000)))))
