from __future__ import annotations

from datetime import date, datetime, time
import os
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    URL,
    and_,
    create_engine,
    delete,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).parent


def get_database_target():
    """
    Cloud priority:
      Streamlit Secrets [database] with host, port, name, user, password.
    Local fallback:
      DATABASE_URL environment variable.
      SQLite database file.
    """
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

    env_value = os.getenv("DATABASE_URL", "").strip()
    if env_value:
        if env_value.startswith("postgres://"):
            return env_value.replace(
                "postgres://", "postgresql+psycopg://", 1
            )
        if env_value.startswith("postgresql://"):
            return env_value.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        return env_value

    return f"sqlite:///{BASE_DIR / 'classroom_booking.db'}"


DATABASE_TARGET = get_database_target()

engine_options: dict[str, Any] = {
    "future": True,
    "pool_pre_ping": True,
}
if isinstance(DATABASE_TARGET, URL):
    engine_options.update(
        {
            "poolclass": NullPool,
            "connect_args": {
                "connect_timeout": 12,
                "sslmode": "require",
            },
        }
    )

engine: Engine = create_engine(DATABASE_TARGET, **engine_options)
metadata = MetaData()

authorized_users = Table(
    "authorized_users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_type", String(20), nullable=False),
    Column("identification_code", String(100), nullable=False),
    Column("name", String(100), nullable=False),
    Column("email", String(255)),
    Column("status", String(20), nullable=False, default="啟用"),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "user_type",
        "identification_code",
        name="uq_authorized_user",
    ),
)

bookings = Table(
    "bookings",
    metadata,
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
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True)),
    Column("cancel_reason", Text),
    Column("cancelled_at", DateTime(timezone=True)),
)

open_periods = Table(
    "open_periods",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("semester", String(30), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

course_blocks = Table(
    "course_blocks",
    metadata,
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
        "semester",
        "room",
        "weekday",
        "start_time",
        "end_time",
        "course_name",
        name="uq_course_block",
    ),
)

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", String(50), nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_id", String(100)),
    Column("detail", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def as_time(value):
    return value if isinstance(value, time) else time.fromisoformat(str(value)[:5])


def rows(result):
    return [dict(row._mapping) for row in result]


def init_db():
    metadata.create_all(engine)


def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, engine.dialect.name
    except Exception as exc:
        return False, str(exc)


def log_action(action, target_type, target_id="", detail=""):
    with engine.begin() as connection:
        connection.execute(
            insert(audit_logs).values(
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                created_at=datetime.now(),
            )
        )


def verify_authorized_user_by_code(user_type, code):
    statement = select(authorized_users).where(
        and_(
            authorized_users.c.user_type == user_type.strip(),
            authorized_users.c.identification_code == code.strip(),
            authorized_users.c.status == "啟用",
        )
    )
    with engine.connect() as connection:
        row = connection.execute(statement).first()
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

    required = {"辨識碼", "姓名"}
    missing = required - set(normalized.keys())
    if missing:
        raise ValueError("Excel 缺少必要欄位：" + "、".join(sorted(missing)))

    work = pd.DataFrame()
    work["辨識碼"] = dataframe[normalized["辨識碼"]]
    work["姓名"] = dataframe[normalized["姓名"]]
    work["聯絡信箱"] = (
        dataframe[normalized["聯絡信箱"]]
        if "聯絡信箱" in normalized
        else ""
    )
    work["狀態"] = (
        dataframe[normalized["狀態"]]
        if "狀態" in normalized
        else "啟用"
    )
    work = work.fillna("")

    for column in ["辨識碼", "姓名", "聯絡信箱", "狀態"]:
        work[column] = work[column].astype(str).str.strip()

    work["辨識碼"] = work["辨識碼"].str.replace(r"\.0$", "", regex=True)

    inserted = updated = skipped = 0
    with engine.begin() as connection:
        if replace:
            connection.execute(
                delete(authorized_users).where(
                    authorized_users.c.user_type == user_type
                )
            )

        for _, row in work.iterrows():
            code = row["辨識碼"]
            name = row["姓名"]
            if not code or not name:
                skipped += 1
                continue

            status = (
                row["狀態"]
                if row["狀態"] in {"啟用", "停用"}
                else "啟用"
            )

            existing = connection.execute(
                select(authorized_users.c.id).where(
                    and_(
                        authorized_users.c.user_type == user_type,
                        authorized_users.c.identification_code == code,
                    )
                )
            ).first()

            values = {
                "name": name,
                "email": row["聯絡信箱"],
                "status": status,
                "imported_at": datetime.now(),
            }

            if existing:
                connection.execute(
                    update(authorized_users)
                    .where(
                        and_(
                            authorized_users.c.user_type == user_type,
                            authorized_users.c.identification_code == code,
                        )
                    )
                    .values(**values)
                )
                updated += 1
            else:
                connection.execute(
                    insert(authorized_users).values(
                        user_type=user_type,
                        identification_code=code,
                        **values,
                    )
                )
                inserted += 1

    log_action(
        "IMPORT",
        "authorized_users",
        user_type,
        f"新增{inserted} 更新{updated}",
    )
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }



def delete_authorized_user(user_type, identification_code):
    with engine.begin() as connection:
        result = connection.execute(
            delete(authorized_users).where(
                and_(
                    authorized_users.c.user_type == user_type,
                    authorized_users.c.identification_code == identification_code,
                )
            )
        )
    deleted = result.rowcount or 0
    if deleted:
        log_action(
            "DELETE",
            "authorized_users",
            f"{user_type}:{identification_code}",
            "管理員刪除名冊資料",
        )
    return deleted


def get_all_authorized_users():
    statement = select(authorized_users).order_by(
        authorized_users.c.user_type,
        authorized_users.c.identification_code,
    )
    with engine.connect() as connection:
        return rows(connection.execute(statement))


def save_open_period(semester, start_date, end_date):
    with engine.begin() as connection:
        connection.execute(update(open_periods).values(is_active=False))
        connection.execute(
            insert(open_periods).values(
                semester=semester,
                start_date=as_date(start_date),
                end_date=as_date(end_date),
                is_active=True,
                created_at=datetime.now(),
            )
        )
    log_action(
        "UPDATE",
        "open_period",
        semester,
        f"{start_date}~{end_date}",
    )


def get_active_open_period():
    statement = (
        select(open_periods)
        .where(open_periods.c.is_active.is_(True))
        .order_by(open_periods.c.id.desc())
        .limit(1)
    )
    with engine.connect() as connection:
        row = connection.execute(statement).first()
    return dict(row._mapping) if row else None


def add_course_blocks(dataframe: pd.DataFrame, semester: str, replace: bool = False):
    required = {"教室", "星期", "開始時間", "結束時間", "課程名稱", "教師"}
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError("Excel 缺少欄位：" + "、".join(sorted(missing)))

    weekday_map = {
        "週一": 0,
        "星期一": 0,
        "週二": 1,
        "星期二": 1,
        "週三": 2,
        "星期三": 2,
        "週四": 3,
        "星期四": 3,
        "週五": 4,
        "星期五": 4,
        "週六": 5,
        "星期六": 5,
        "週日": 6,
        "星期日": 6,
    }

    inserted = duplicates = skipped = 0
    with engine.begin() as connection:
        if replace:
            connection.execute(
                delete(course_blocks).where(
                    course_blocks.c.semester == semester
                )
            )

        for _, row in dataframe.fillna("").iterrows():
            weekday = weekday_map.get(str(row["星期"]).strip())
            room = str(row["教室"]).strip()
            start = str(row["開始時間"]).strip()
            end = str(row["結束時間"]).strip()
            name = str(row["課程名稱"]).strip()
            teacher = str(row["教師"]).strip()

            if (
                weekday is None
                or not room
                or not start
                or not end
                or not name
                or start[:5] >= end[:5]
            ):
                skipped += 1
                continue

            try:
                connection.execute(
                    insert(course_blocks).values(
                        semester=semester,
                        room=room,
                        weekday=weekday,
                        start_time=as_time(start),
                        end_time=as_time(end),
                        course_name=name,
                        teacher=teacher,
                        is_active=True,
                        created_at=datetime.now(),
                    )
                )
                inserted += 1
            except IntegrityError:
                duplicates += 1

    log_action(
        "IMPORT",
        "course_blocks",
        semester,
        f"新增{inserted} 重複{duplicates} 略過{skipped}",
    )
    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "skipped": skipped,
    }


def get_course_semesters():
    statement = (
        select(
            course_blocks.c.semester,
            func.count().label("course_count"),
            func.max(course_blocks.c.is_active).label("is_active"),
        )
        .group_by(course_blocks.c.semester)
        .order_by(course_blocks.c.semester.desc())
    )
    with engine.connect() as connection:
        return rows(connection.execute(statement))


def set_course_semester_active(semester, active):
    with engine.begin() as connection:
        connection.execute(
            update(course_blocks)
            .where(course_blocks.c.semester == semester)
            .values(is_active=bool(active))
        )


def delete_course_semester(semester):
    with engine.begin() as connection:
        result = connection.execute(
            delete(course_blocks).where(
                course_blocks.c.semester == semester
            )
        )
        return result.rowcount or 0


def get_course_blocks(booking_date, room, semester=None):
    booking_day = as_date(booking_date)

    if semester is None:
        period = get_active_open_period()
        semester = period["semester"] if period else None

    conditions = [
        course_blocks.c.room == room,
        course_blocks.c.weekday == booking_day.weekday(),
        course_blocks.c.is_active.is_(True),
    ]
    if semester:
        conditions.append(course_blocks.c.semester == semester)

    statement = (
        select(course_blocks)
        .where(and_(*conditions))
        .order_by(course_blocks.c.start_time)
    )
    with engine.connect() as connection:
        return rows(connection.execute(statement))


def check_booking_conflict(
    booking_date,
    room,
    start_time,
    end_time,
    exclude_booking_id=None,
):
    start_object = as_time(start_time)
    end_object = as_time(end_time)

    for course in get_course_blocks(booking_date, room):
        if (
            start_object < course["end_time"]
            and end_object > course["start_time"]
        ):
            return {
                "type": "course",
                "detail": course["course_name"],
            }

    conditions = [
        bookings.c.booking_date == as_date(booking_date),
        bookings.c.room == room,
        bookings.c.status == "有效",
        start_object < bookings.c.end_time,
        end_object > bookings.c.start_time,
    ]
    if exclude_booking_id:
        conditions.append(
            bookings.c.booking_id != exclude_booking_id
        )

    statement = (
        select(bookings.c.booking_id)
        .where(and_(*conditions))
        .limit(1)
    )
    with engine.connect() as connection:
        row = connection.execute(statement).first()

    return (
        {
            "type": "booking",
            "detail": row._mapping["booking_id"],
        }
        if row
        else None
    )


def create_booking(
    booking_date,
    room,
    start_time,
    end_time,
    applicant_type,
    applicant_name,
    identification_code,
    phone,
    email,
    reason,
):
    with engine.begin() as connection:
        result = connection.execute(
            insert(bookings).values(
                booking_id=None,
                booking_date=as_date(booking_date),
                room=room,
                start_time=as_time(start_time),
                end_time=as_time(end_time),
                applicant_type=applicant_type,
                applicant_name=applicant_name,
                identification_code=identification_code,
                phone=phone,
                email=email,
                reason=reason,
                status="有效",
                created_at=datetime.now(),
            )
        )
        row_id = int(result.inserted_primary_key[0])
        booking_id = (
            f"AU-PSY-{as_date(booking_date).strftime('%Y%m%d')}-"
            f"{row_id:05d}"
        )
        connection.execute(
            update(bookings)
            .where(bookings.c.id == row_id)
            .values(booking_id=booking_id)
        )

    log_action(
        "CREATE",
        "booking",
        booking_id,
        f"{room} {start_time}-{end_time}",
    )
    return booking_id



def get_user_bookings(user_type, identification_code, limit=100):
    safe_limit = max(1, min(int(limit), 1000))
    statement = (
        select(bookings)
        .where(
            and_(
                bookings.c.applicant_type == user_type,
                bookings.c.identification_code == identification_code,
            )
        )
        .order_by(bookings.c.booking_date.desc(), bookings.c.start_time.desc())
        .limit(safe_limit)
    )
    with engine.connect() as connection:
        return rows(connection.execute(statement))


def record_login(user_type, identification_code, name, success=True):
    detail = f"name={name}; success={success}"
    log_action(
        "LOGIN_SUCCESS" if success else "LOGIN_FAILED",
        "user",
        f"{user_type}:{identification_code}",
        detail,
    )


def record_logout(user_type, identification_code, name):
    log_action(
        "LOGOUT",
        "user",
        f"{user_type}:{identification_code}",
        f"name={name}",
    )


def get_all_bookings():
    statement = select(bookings).order_by(
        bookings.c.booking_date.desc(),
        bookings.c.start_time.desc(),
    )
    with engine.connect() as connection:
        return rows(connection.execute(statement))


def get_booking_by_id(booking_id):
    with engine.connect() as connection:
        row = connection.execute(
            select(bookings).where(
                bookings.c.booking_id == booking_id
            )
        ).first()
    return dict(row._mapping) if row else None


def update_booking(
    booking_id,
    booking_date,
    room,
    start_time,
    end_time,
    reason,
):
    with engine.begin() as connection:
        connection.execute(
            update(bookings)
            .where(
                and_(
                    bookings.c.booking_id == booking_id,
                    bookings.c.status == "有效",
                )
            )
            .values(
                booking_date=as_date(booking_date),
                room=room,
                start_time=as_time(start_time),
                end_time=as_time(end_time),
                reason=reason,
                updated_at=datetime.now(),
            )
        )


def cancel_booking(booking_id, cancel_reason):
    with engine.begin() as connection:
        connection.execute(
            update(bookings)
            .where(
                and_(
                    bookings.c.booking_id == booking_id,
                    bookings.c.status == "有效",
                )
            )
            .values(
                status="已取消",
                cancel_reason=cancel_reason,
                cancelled_at=datetime.now(),
            )
        )


def get_dashboard_counts():
    with engine.connect() as connection:
        teachers = connection.execute(
            select(func.count())
            .select_from(authorized_users)
            .where(
                and_(
                    authorized_users.c.user_type == "教師",
                    authorized_users.c.status == "啟用",
                )
            )
        ).scalar_one()

        students = connection.execute(
            select(func.count())
            .select_from(authorized_users)
            .where(
                and_(
                    authorized_users.c.user_type == "學生",
                    authorized_users.c.status == "啟用",
                )
            )
        ).scalar_one()

        active = connection.execute(
            select(func.count())
            .select_from(bookings)
            .where(bookings.c.status == "有效")
        ).scalar_one()

    return {
        "teachers": teachers,
        "students": students,
        "active_bookings": active,
    }


def get_audit_logs(limit=1000):
    safe_limit = max(1, min(int(limit), 5000))
    statement = (
        select(audit_logs)
        .order_by(audit_logs.c.id.desc())
        .limit(safe_limit)
    )
    with engine.connect() as connection:
        return rows(connection.execute(statement))
