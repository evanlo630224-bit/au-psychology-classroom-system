from __future__ import annotations

from datetime import date, datetime, time
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, MetaData, String, Table, Text,
    Time, UniqueConstraint, URL, and_, create_engine, delete, func, insert,
    inspect, or_, select, text, update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).parent


def get_database_target():
    try:
        import streamlit as st
        if "database" in st.secrets:
            cfg = st.secrets["database"]
            required = {"host", "port", "name", "user", "password"}
            if required.issubset(set(cfg.keys())):
                return URL.create(
                    drivername="postgresql+psycopg",
                    username=str(cfg["user"]).strip(),
                    password=str(cfg["password"]),
                    host=str(cfg["host"]).strip(),
                    port=int(cfg["port"]),
                    database=str(cfg["name"]).strip(),
                )
    except Exception:
        pass

    value = os.getenv("DATABASE_URL", "").strip()
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value:
        return value
    return f"sqlite:///{BASE_DIR / 'classroom_booking.db'}"


DATABASE_TARGET = get_database_target()
engine_options: dict[str, Any] = {"future": True, "pool_pre_ping": True}
if isinstance(DATABASE_TARGET, URL):
    engine_options.update({
        "poolclass": NullPool,
        "connect_args": {"connect_timeout": 12, "sslmode": "require"},
    })

engine: Engine = create_engine(DATABASE_TARGET, **engine_options)
metadata = MetaData()

authorized_users = Table(
    "authorized_users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_type", String(20), nullable=False),
    Column("identification_code", String(100), nullable=False),
    Column("name", String(100), nullable=False),
    Column("email", String(255)),
    Column("status", String(20), nullable=False, default="啟用"),
    Column("imported_at", DateTime(timezone=True), nullable=False),
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
    Column("status", String(20), nullable=False, default="待審核"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True)),
    Column("cancel_reason", Text),
    Column("cancelled_at", DateTime(timezone=True)),
    Column("review_note", Text),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("reviewed_by", String(100)),
    Column("qr_token", String(100)),
)

open_periods = Table(
    "open_periods", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("semester", String(30), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
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
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "semester", "room", "weekday", "start_time", "end_time", "course_name",
        name="uq_course_block",
    ),
)

audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", String(50), nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_id", String(100)),
    Column("detail", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

classrooms = Table(
    "classrooms", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("room_name", String(30), nullable=False, unique=True),
    Column("capacity", Integer),
    Column("location", String(255)),
    Column("equipment", Text),
    Column("status", String(20), nullable=False, default="啟用"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True)),
)

announcements = Table(
    "announcements", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(255), nullable=False),
    Column("content", Text, nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

closures = Table(
    "closures", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("closure_date", Date, nullable=False),
    Column("room", String(30)),
    Column("reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

system_settings = Table(
    "system_settings", metadata,
    Column("setting_key", String(100), primary_key=True),
    Column("setting_value", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def as_time(value):
    return value if isinstance(value, time) else time.fromisoformat(str(value)[:5])


def rows(result):
    return [dict(row._mapping) for row in result]


def _migrate_existing_schema():
    inspector = inspect(engine)
    if "bookings" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("bookings")}
    additions = {
        "review_note": "TEXT",
        "reviewed_at": "TIMESTAMP",
        "reviewed_by": "VARCHAR(100)",
        "qr_token": "VARCHAR(100)",
    }
    with engine.begin() as conn:
        for name, sql_type in additions.items():
            if name not in existing:
                if engine.dialect.name == "postgresql":
                    conn.execute(text(f'ALTER TABLE bookings ADD COLUMN IF NOT EXISTS {name} {sql_type}'))
                else:
                    conn.execute(text(f'ALTER TABLE bookings ADD COLUMN {name} {sql_type}'))


def init_db():
    metadata.create_all(engine)
    _migrate_existing_schema()
    defaults = [
        ("M502", 40), ("M506", 40), ("M507", 40), ("M510", 40), ("800A", 30)
    ]
    with engine.begin() as conn:
        for room_name, capacity in defaults:
            exists = conn.execute(
                select(classrooms.c.id).where(classrooms.c.room_name == room_name)
            ).first()
            if not exists:
                conn.execute(insert(classrooms).values(
                    room_name=room_name, capacity=capacity, location="",
                    equipment="", status="啟用", created_at=datetime.now()
                ))
        for key, value in {
            "approval_mode": "manual",
            "max_days_ahead": "180",
        }.items():
            exists = conn.execute(
                select(system_settings.c.setting_key).where(
                    system_settings.c.setting_key == key
                )
            ).first()
            if not exists:
                conn.execute(insert(system_settings).values(
                    setting_key=key, setting_value=value, updated_at=datetime.now()
                ))


def database_health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, engine.dialect.name
    except Exception as exc:
        return False, str(exc)


def log_action(action, target_type, target_id="", detail=""):
    with engine.begin() as conn:
        conn.execute(insert(audit_logs).values(
            action=action, target_type=target_type, target_id=target_id,
            detail=detail, created_at=datetime.now()
        ))


def get_setting(key, default=""):
    with engine.connect() as conn:
        row = conn.execute(
            select(system_settings.c.setting_value).where(
                system_settings.c.setting_key == key
            )
        ).first()
    return row._mapping["setting_value"] if row else default


def set_setting(key, value):
    with engine.begin() as conn:
        exists = conn.execute(
            select(system_settings.c.setting_key).where(
                system_settings.c.setting_key == key
            )
        ).first()
        if exists:
            conn.execute(update(system_settings).where(
                system_settings.c.setting_key == key
            ).values(setting_value=str(value), updated_at=datetime.now()))
        else:
            conn.execute(insert(system_settings).values(
                setting_key=key, setting_value=str(value), updated_at=datetime.now()
            ))
    log_action("UPDATE", "setting", key, str(value))


def verify_authorized_user_by_code(user_type, code):
    statement = select(authorized_users).where(and_(
        authorized_users.c.user_type == user_type.strip(),
        authorized_users.c.identification_code == code.strip(),
        authorized_users.c.status == "啟用",
    ))
    with engine.connect() as conn:
        row = conn.execute(statement).first()
    return dict(row._mapping) if row else None


def import_authorized_users(dataframe: pd.DataFrame, user_type: str, replace: bool):
    aliases = {
        "辨識碼": ["辨識碼", "教師職編", "學生學號", "職編", "學號", "identification_code", "id"],
        "姓名": ["姓名", "name"],
        "聯絡信箱": ["聯絡信箱", "Email", "email", "電子郵件"],
        "狀態": ["狀態", "status"],
    }
    normalized = {}
    for target, candidates in aliases.items():
        for candidate in candidates:
            if candidate in dataframe.columns:
                normalized[target] = candidate
                break
    missing = {"辨識碼", "姓名"} - set(normalized.keys())
    if missing:
        raise ValueError("Excel 缺少必要欄位：" + "、".join(sorted(missing)))

    work = pd.DataFrame()
    work["辨識碼"] = dataframe[normalized["辨識碼"]]
    work["姓名"] = dataframe[normalized["姓名"]]
    work["聯絡信箱"] = dataframe[normalized["聯絡信箱"]] if "聯絡信箱" in normalized else ""
    work["狀態"] = dataframe[normalized["狀態"]] if "狀態" in normalized else "啟用"
    work = work.fillna("")
    for col in work.columns:
        work[col] = work[col].astype(str).str.strip()
    work["辨識碼"] = work["辨識碼"].str.replace(r"\.0$", "", regex=True)

    inserted = updated = skipped = 0
    with engine.begin() as conn:
        if replace:
            conn.execute(delete(authorized_users).where(
                authorized_users.c.user_type == user_type
            ))
        for _, row in work.iterrows():
            code, name = row["辨識碼"], row["姓名"]
            if not code or not name:
                skipped += 1
                continue
            status = row["狀態"] if row["狀態"] in {"啟用", "停用"} else "啟用"
            exists = conn.execute(select(authorized_users.c.id).where(and_(
                authorized_users.c.user_type == user_type,
                authorized_users.c.identification_code == code,
            ))).first()
            values = {
                "name": name, "email": row["聯絡信箱"],
                "status": status, "imported_at": datetime.now()
            }
            if exists:
                conn.execute(update(authorized_users).where(and_(
                    authorized_users.c.user_type == user_type,
                    authorized_users.c.identification_code == code,
                )).values(**values))
                updated += 1
            else:
                conn.execute(insert(authorized_users).values(
                    user_type=user_type, identification_code=code, **values
                ))
                inserted += 1
    log_action("IMPORT", "authorized_users", user_type, f"新增{inserted} 更新{updated}")
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def get_all_authorized_users():
    with engine.connect() as conn:
        return rows(conn.execute(
            select(authorized_users).order_by(
                authorized_users.c.user_type,
                authorized_users.c.identification_code,
            )
        ))


def delete_authorized_user(user_type, identification_code):
    with engine.begin() as conn:
        result = conn.execute(delete(authorized_users).where(and_(
            authorized_users.c.user_type == user_type,
            authorized_users.c.identification_code == identification_code,
        )))
    return result.rowcount or 0


def get_classrooms(active_only=False):
    statement = select(classrooms)
    if active_only:
        statement = statement.where(classrooms.c.status == "啟用")
    statement = statement.order_by(classrooms.c.room_name)
    with engine.connect() as conn:
        return rows(conn.execute(statement))


def save_classroom(room_name, capacity, location, equipment, status):
    with engine.begin() as conn:
        exists = conn.execute(
            select(classrooms.c.id).where(classrooms.c.room_name == room_name)
        ).first()
        values = {
            "capacity": int(capacity), "location": location,
            "equipment": equipment, "status": status, "updated_at": datetime.now(),
        }
        if exists:
            conn.execute(update(classrooms).where(
                classrooms.c.room_name == room_name
            ).values(**values))
        else:
            conn.execute(insert(classrooms).values(
                room_name=room_name, created_at=datetime.now(), **values
            ))
    log_action("UPSERT", "classroom", room_name, status)


def delete_classroom(room_name):
    with engine.begin() as conn:
        result = conn.execute(delete(classrooms).where(
            classrooms.c.room_name == room_name
        ))
    return result.rowcount or 0


def save_open_period(semester, start_date, end_date):
    with engine.begin() as conn:
        conn.execute(update(open_periods).values(is_active=False))
        conn.execute(insert(open_periods).values(
            semester=semester, start_date=as_date(start_date),
            end_date=as_date(end_date), is_active=True, created_at=datetime.now()
        ))


def get_active_open_period():
    with engine.connect() as conn:
        row = conn.execute(
            select(open_periods).where(open_periods.c.is_active.is_(True))
            .order_by(open_periods.c.id.desc()).limit(1)
        ).first()
    return dict(row._mapping) if row else None


def add_course_blocks(dataframe, semester, replace=False):
    required = {"教室", "星期", "開始時間", "結束時間", "課程名稱", "教師"}
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError("Excel 缺少欄位：" + "、".join(sorted(missing)))
    weekday_map = {
        "週一":0,"星期一":0,"週二":1,"星期二":1,"週三":2,"星期三":2,
        "週四":3,"星期四":3,"週五":4,"星期五":4,"週六":5,"星期六":5,
        "週日":6,"星期日":6,
    }
    inserted = duplicates = skipped = 0
    with engine.begin() as conn:
        if replace:
            conn.execute(delete(course_blocks).where(course_blocks.c.semester == semester))
        for _, row in dataframe.fillna("").iterrows():
            wd = weekday_map.get(str(row["星期"]).strip())
            room = str(row["教室"]).strip()
            start = str(row["開始時間"]).strip()[:5]
            end = str(row["結束時間"]).strip()[:5]
            name = str(row["課程名稱"]).strip()
            teacher = str(row["教師"]).strip()
            if wd is None or not room or not start or not end or not name or start >= end:
                skipped += 1
                continue
            try:
                conn.execute(insert(course_blocks).values(
                    semester=semester, room=room, weekday=wd,
                    start_time=as_time(start), end_time=as_time(end),
                    course_name=name, teacher=teacher, is_active=True,
                    created_at=datetime.now(),
                ))
                inserted += 1
            except IntegrityError:
                duplicates += 1
    return {"inserted": inserted, "duplicates": duplicates, "skipped": skipped}


def get_course_semesters():
    """Return semester summaries without applying MAX() to a Boolean column.

    PostgreSQL does not support max(boolean). bool_or() is used on PostgreSQL,
    while max() remains suitable for SQLite's integer-backed Boolean values.
    """
    active_summary = (
        func.bool_or(course_blocks.c.is_active)
        if engine.dialect.name == "postgresql"
        else func.max(course_blocks.c.is_active)
    )

    statement = (
        select(
            course_blocks.c.semester,
            func.count().label("course_count"),
            active_summary.label("is_active"),
        )
        .group_by(course_blocks.c.semester)
        .order_by(course_blocks.c.semester.desc())
    )

    with engine.connect() as conn:
        return rows(conn.execute(statement))


def set_course_semester_active(semester, active):
    with engine.begin() as conn:
        conn.execute(update(course_blocks).where(
            course_blocks.c.semester == semester
        ).values(is_active=bool(active)))


def delete_course_semester(semester):
    with engine.begin() as conn:
        result = conn.execute(delete(course_blocks).where(
            course_blocks.c.semester == semester
        ))
    return result.rowcount or 0


def get_course_blocks(booking_date, room, semester=None):
    day = as_date(booking_date)
    if semester is None:
        period = get_active_open_period()
        semester = period["semester"] if period else None
    conditions = [
        course_blocks.c.room == room,
        course_blocks.c.weekday == day.weekday(),
        course_blocks.c.is_active.is_(True),
    ]
    if semester:
        conditions.append(course_blocks.c.semester == semester)
    with engine.connect() as conn:
        return rows(conn.execute(
            select(course_blocks).where(and_(*conditions))
            .order_by(course_blocks.c.start_time)
        ))


def save_closure(closure_date, room, reason):
    with engine.begin() as conn:
        conn.execute(insert(closures).values(
            closure_date=as_date(closure_date), room=room or None,
            reason=reason, created_at=datetime.now()
        ))
    log_action(
        "CREATE", "closure", str(closure_date),
        f"room={room or 'ALL'}; reason={reason}",
    )


def get_closures():
    with engine.connect() as conn:
        return rows(conn.execute(
            select(closures).order_by(closures.c.closure_date.desc())
        ))


def delete_closure(closure_id):
    with engine.begin() as conn:
        result = conn.execute(delete(closures).where(closures.c.id == int(closure_id)))
    return result.rowcount or 0


def get_closure_for(booking_date, room):
    with engine.connect() as conn:
        row = conn.execute(select(closures).where(and_(
            closures.c.closure_date == as_date(booking_date),
            or_(closures.c.room.is_(None), closures.c.room == "", closures.c.room == room),
        )).limit(1)).first()
    return dict(row._mapping) if row else None


def check_booking_conflict(booking_date, room, start_time, end_time, exclude_booking_id=None):
    closure = get_closure_for(booking_date, room)
    if closure:
        return {"type": "closure", "detail": closure["reason"]}

    start_obj, end_obj = as_time(start_time), as_time(end_time)
    for course in get_course_blocks(booking_date, room):
        if start_obj < course["end_time"] and end_obj > course["start_time"]:
            return {"type": "course", "detail": course["course_name"]}

    conditions = [
        bookings.c.booking_date == as_date(booking_date),
        bookings.c.room == room,
        bookings.c.status.in_(["待審核", "已核准", "有效"]),
        start_obj < bookings.c.end_time,
        end_obj > bookings.c.start_time,
    ]
    if exclude_booking_id:
        conditions.append(bookings.c.booking_id != exclude_booking_id)
    with engine.connect() as conn:
        row = conn.execute(select(bookings.c.booking_id).where(
            and_(*conditions)
        ).limit(1)).first()
    return {"type": "booking", "detail": row._mapping["booking_id"]} if row else None


def create_booking(booking_date, room, start_time, end_time, applicant_type,
                   applicant_name, identification_code, phone, email, reason):
    approval_mode = get_setting("approval_mode", "manual")
    status = "已核准" if approval_mode == "auto" else "待審核"
    with engine.begin() as conn:
        result = conn.execute(insert(bookings).values(
            booking_id=None, booking_date=as_date(booking_date), room=room,
            start_time=as_time(start_time), end_time=as_time(end_time),
            applicant_type=applicant_type, applicant_name=applicant_name,
            identification_code=identification_code, phone=phone, email=email,
            reason=reason, status=status, created_at=datetime.now(),
            qr_token=str(uuid4()),
        ))
        row_id = int(result.inserted_primary_key[0])
        booking_id = f"AU-PSY-{as_date(booking_date).strftime('%Y%m%d')}-{row_id:05d}"
        conn.execute(update(bookings).where(bookings.c.id == row_id).values(
            booking_id=booking_id
        ))
    log_action("CREATE", "booking", booking_id, status)
    return booking_id, status


def get_all_bookings(filters=None):
    statement = select(bookings)
    filters = filters or {}
    if filters.get("room"):
        statement = statement.where(bookings.c.room == filters["room"])
    if filters.get("status"):
        statement = statement.where(bookings.c.status == filters["status"])
    if filters.get("date_from"):
        statement = statement.where(bookings.c.booking_date >= as_date(filters["date_from"]))
    if filters.get("date_to"):
        statement = statement.where(bookings.c.booking_date <= as_date(filters["date_to"]))
    if filters.get("keyword"):
        keyword = f'%{filters["keyword"]}%'
        statement = statement.where(or_(
            bookings.c.applicant_name.ilike(keyword),
            bookings.c.identification_code.ilike(keyword),
            bookings.c.reason.ilike(keyword),
            bookings.c.booking_id.ilike(keyword),
        ))
    statement = statement.order_by(bookings.c.booking_date.desc(), bookings.c.start_time.desc())
    with engine.connect() as conn:
        return rows(conn.execute(statement))


def get_user_bookings(user_type, identification_code, limit=200):
    with engine.connect() as conn:
        return rows(conn.execute(
            select(bookings).where(and_(
                bookings.c.applicant_type == user_type,
                bookings.c.identification_code == identification_code,
            )).order_by(bookings.c.booking_date.desc(), bookings.c.start_time.desc())
            .limit(max(1, min(int(limit), 1000)))
        ))


def get_booking_by_id(booking_id):
    with engine.connect() as conn:
        row = conn.execute(select(bookings).where(
            bookings.c.booking_id == booking_id
        )).first()
    return dict(row._mapping) if row else None


def review_booking(booking_id, new_status, reviewer, note=""):
    with engine.begin() as conn:
        conn.execute(update(bookings).where(
            bookings.c.booking_id == booking_id
        ).values(
            status=new_status, review_note=note,
            reviewed_at=datetime.now(), reviewed_by=reviewer,
            updated_at=datetime.now(),
        ))
    log_action("REVIEW", "booking", booking_id, f"{new_status}; {note}")


def cancel_booking(booking_id, cancel_reason):
    with engine.begin() as conn:
        conn.execute(update(bookings).where(
            bookings.c.booking_id == booking_id
        ).values(
            status="已取消", cancel_reason=cancel_reason,
            cancelled_at=datetime.now(), updated_at=datetime.now(),
        ))
    log_action("CANCEL", "booking", booking_id, cancel_reason)


def save_announcement(title, content, start_date, end_date, is_active=True):
    with engine.begin() as conn:
        conn.execute(insert(announcements).values(
            title=title, content=content,
            start_date=as_date(start_date), end_date=as_date(end_date),
            is_active=bool(is_active), created_at=datetime.now(),
        ))
    log_action("CREATE", "announcement", title, f"{start_date}~{end_date}")


def get_announcements(active_only=False):
    statement = select(announcements)
    if active_only:
        today = date.today()
        statement = statement.where(and_(
            announcements.c.is_active.is_(True),
            announcements.c.start_date <= today,
            announcements.c.end_date >= today,
        ))
    statement = statement.order_by(announcements.c.id.desc())
    with engine.connect() as conn:
        return rows(conn.execute(statement))


def delete_announcement(announcement_id):
    with engine.begin() as conn:
        result = conn.execute(delete(announcements).where(
            announcements.c.id == int(announcement_id)
        ))
    return result.rowcount or 0


def get_dashboard_counts():
    today = date.today()
    with engine.connect() as conn:
        teachers = conn.execute(select(func.count()).select_from(authorized_users).where(and_(
            authorized_users.c.user_type == "教師",
            authorized_users.c.status == "啟用",
        ))).scalar_one()
        students = conn.execute(select(func.count()).select_from(authorized_users).where(and_(
            authorized_users.c.user_type == "學生",
            authorized_users.c.status == "啟用",
        ))).scalar_one()
        active = conn.execute(select(func.count()).select_from(bookings).where(
            bookings.c.status.in_(["待審核", "已核准", "有效"])
        )).scalar_one()
        pending = conn.execute(select(func.count()).select_from(bookings).where(
            bookings.c.status == "待審核"
        )).scalar_one()
        today_count = conn.execute(select(func.count()).select_from(bookings).where(and_(
            bookings.c.booking_date == today,
            bookings.c.status.in_(["待審核", "已核准", "有效"]),
        ))).scalar_one()
    return {
        "teachers": teachers, "students": students, "active_bookings": active,
        "pending": pending, "today": today_count,
    }


def get_audit_logs(limit=1000):
    with engine.connect() as conn:
        return rows(conn.execute(
            select(audit_logs).order_by(audit_logs.c.id.desc())
            .limit(max(1, min(int(limit), 5000)))
        ))


def record_login(user_type, identification_code, name, success=True):
    log_action(
        "LOGIN_SUCCESS" if success else "LOGIN_FAILED",
        "user", f"{user_type}:{identification_code}",
        f"name={name}; success={success}",
    )


def record_logout(user_type, identification_code, name):
    log_action("LOGOUT", "user", f"{user_type}:{identification_code}", f"name={name}")
