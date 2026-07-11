from datetime import datetime
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Boolean, Column, DateTime, Integer, MetaData, String, Table, Text,
    UniqueConstraint, and_, create_engine, delete, func, insert, select, update, text
)
from sqlalchemy.exc import IntegrityError

BASE_DIR = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'classroom_booking.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
metadata = MetaData()

authorized_users = Table(
    "authorized_users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_type", String(20), nullable=False),
    Column("identification_code", String(100), nullable=False),
    Column("name", String(100), nullable=False),
    Column("email", String(255)),
    Column("status", String(20), nullable=False, default="啟用"),
    Column("imported_at", String(30), nullable=False),
    UniqueConstraint("user_type", "identification_code", name="uq_user_type_code"),
)

bookings = Table(
    "bookings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("booking_id", String(100), unique=True),
    Column("booking_date", String(10), nullable=False),
    Column("room", String(30), nullable=False),
    Column("start_time", String(5), nullable=False),
    Column("end_time", String(5), nullable=False),
    Column("applicant_type", String(20), nullable=False),
    Column("applicant_name", String(100), nullable=False),
    Column("identification_code", String(100)),
    Column("phone", String(50), nullable=False),
    Column("email", String(255), nullable=False),
    Column("reason", Text, nullable=False),
    Column("status", String(20), nullable=False, default="有效"),
    Column("created_at", String(30), nullable=False),
    Column("updated_at", String(30)),
    Column("cancel_reason", Text),
    Column("cancelled_at", String(30)),
)

open_periods = Table(
    "open_periods", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("semester", String(30), nullable=False),
    Column("start_date", String(10), nullable=False),
    Column("end_date", String(10), nullable=False),
    Column("is_active", Integer, nullable=False, default=1),
    Column("created_at", String(30), nullable=False),
)

course_blocks = Table(
    "course_blocks", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("room", String(30), nullable=False),
    Column("weekday", Integer, nullable=False),
    Column("start_time", String(5), nullable=False),
    Column("end_time", String(5), nullable=False),
    Column("course_name", String(255), nullable=False),
    Column("teacher", String(100)),
    Column("created_at", String(30), nullable=False),
    Column("semester", String(30), nullable=False, default="未分類"),
    Column("is_active", Integer, nullable=False, default=1),
    UniqueConstraint(
        "semester", "room", "weekday", "start_time", "end_time",
        "course_name", "teacher", name="uq_course_block"
    ),
)

audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", String(50), nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_id", String(100)),
    Column("detail", Text),
    Column("created_at", String(30), nullable=False),
)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def rows_to_dicts(result):
    return [dict(row._mapping) for row in result]

def init_db():
    metadata.create_all(engine)

def get_database_backend():
    return "PostgreSQL" if engine.dialect.name == "postgresql" else "SQLite"

def database_health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"{get_database_backend()} 連線正常。"
    except Exception as exc:
        return False, f"資料庫連線失敗：{exc}"

def log_action(action, target_type, target_id="", detail=""):
    with engine.begin() as conn:
        conn.execute(insert(audit_logs).values(
            action=action, target_type=target_type, target_id=target_id,
            detail=detail, created_at=now_text()
        ))

def verify_authorized_user_by_code(user_type, identification_code):
    stmt = select(authorized_users).where(and_(
        authorized_users.c.user_type == user_type.strip(),
        authorized_users.c.identification_code == identification_code.strip(),
        authorized_users.c.status == "啟用",
    ))
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
    return dict(row._mapping) if row else None

def import_authorized_users(dataframe: pd.DataFrame, user_type: str, replace: bool):
    required = {"辨識碼", "姓名", "聯絡信箱", "狀態"}
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError("Excel 缺少欄位：" + "、".join(sorted(missing)))
    df = dataframe.copy()
    for col in required:
        df[col] = df[col].astype(str).str.strip()
    inserted = updated = skipped = 0
    imported_at = now_text()
    with engine.begin() as conn:
        if replace:
            conn.execute(delete(authorized_users).where(authorized_users.c.user_type == user_type))
        for _, row in df.iterrows():
            code, name = row["辨識碼"], row["姓名"]
            email, status = row["聯絡信箱"], row["狀態"] or "啟用"
            if not code or not name:
                skipped += 1; continue
            if status not in {"啟用", "停用"}: status = "啟用"
            existing = conn.execute(select(authorized_users.c.id).where(and_(
                authorized_users.c.user_type == user_type,
                authorized_users.c.identification_code == code,
            ))).first()
            if existing:
                conn.execute(update(authorized_users).where(and_(
                    authorized_users.c.user_type == user_type,
                    authorized_users.c.identification_code == code,
                )).values(name=name, email=email, status=status, imported_at=imported_at))
                updated += 1
            else:
                conn.execute(insert(authorized_users).values(
                    user_type=user_type, identification_code=code, name=name,
                    email=email, status=status, imported_at=imported_at
                ))
                inserted += 1
    log_action("IMPORT", "authorized_users", user_type, f"新增{inserted} 更新{updated}")
    return {"inserted": inserted, "updated": updated, "skipped": skipped}

def get_all_authorized_users():
    stmt = select(
        authorized_users.c.user_type.label("身份"),
        authorized_users.c.identification_code.label("辨識碼"),
        authorized_users.c.name.label("姓名"),
        authorized_users.c.email.label("Email"),
        authorized_users.c.status.label("狀態"),
        authorized_users.c.imported_at.label("匯入時間"),
    ).order_by(authorized_users.c.user_type, authorized_users.c.identification_code)
    with engine.connect() as conn:
        return rows_to_dicts(conn.execute(stmt))

def save_open_period(semester, start_date, end_date):
    with engine.begin() as conn:
        conn.execute(update(open_periods).values(is_active=0))
        conn.execute(insert(open_periods).values(semester=semester, start_date=start_date,
            end_date=end_date, is_active=1, created_at=now_text()))
    log_action("UPDATE", "open_period", semester, f"{start_date}~{end_date}")

def get_active_open_period():
    stmt = select(open_periods.c.semester, open_periods.c.start_date, open_periods.c.end_date).where(
        open_periods.c.is_active == 1
    ).order_by(open_periods.c.id.desc()).limit(1)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
    return dict(row._mapping) if row else None

def add_course_blocks(dataframe: pd.DataFrame, semester: str, replace: bool = False):
    required = {"教室", "星期", "開始時間", "結束時間", "課程名稱", "教師"}
    missing = required - set(dataframe.columns)
    if missing: raise ValueError("Excel 缺少欄位：" + "、".join(sorted(missing)))
    semester = semester.strip()
    if not semester: raise ValueError("學期不可空白")
    weekday_map = {"週一":0,"星期一":0,"週二":1,"星期二":1,"週三":2,"星期三":2,
        "週四":3,"星期四":3,"週五":4,"星期五":4,"週六":5,"星期六":5,"週日":6,"星期日":6}
    inserted = duplicates = skipped = 0
    with engine.begin() as conn:
        if replace:
            conn.execute(delete(course_blocks).where(course_blocks.c.semester == semester))
        for _, row in dataframe.fillna("").iterrows():
            weekday = weekday_map.get(str(row["星期"]).strip())
            room = str(row["教室"]).strip(); start = str(row["開始時間"]).strip()
            end = str(row["結束時間"]).strip(); name = str(row["課程名稱"]).strip()
            teacher = str(row["教師"]).strip()
            if weekday is None or not room or not start or not end or not name or start >= end:
                skipped += 1; continue
            try:
                conn.execute(insert(course_blocks).values(semester=semester, room=room, weekday=weekday,
                    start_time=start, end_time=end, course_name=name, teacher=teacher,
                    is_active=1, created_at=now_text()))
                inserted += 1
            except IntegrityError:
                duplicates += 1
    log_action("IMPORT", "course_blocks", semester, f"新增{inserted} 重複{duplicates} 略過{skipped}")
    return {"inserted": inserted, "duplicates": duplicates, "skipped": skipped}

def get_course_semesters():
    stmt = select(
        course_blocks.c.semester,
        func.count().label("course_count"),
        func.max(course_blocks.c.is_active).label("is_active"),
        func.max(course_blocks.c.created_at).label("last_imported_at"),
    ).group_by(course_blocks.c.semester).order_by(course_blocks.c.semester.desc())
    with engine.connect() as conn:
        return rows_to_dicts(conn.execute(stmt))

def set_course_semester_active(semester, is_active):
    with engine.begin() as conn:
        conn.execute(update(course_blocks).where(course_blocks.c.semester == semester).values(is_active=1 if is_active else 0))
    log_action("UPDATE", "course_semester", semester, f"is_active={int(is_active)}")

def delete_course_semester(semester):
    with engine.begin() as conn:
        result = conn.execute(delete(course_blocks).where(course_blocks.c.semester == semester))
        deleted = result.rowcount or 0
    log_action("DELETE", "course_semester", semester, f"刪除{deleted}筆")
    return deleted

def get_course_blocks(booking_date, room, semester=None):
    weekday = datetime.strptime(booking_date, "%Y-%m-%d").weekday()
    if semester is None:
        period = get_active_open_period(); semester = period["semester"] if period else None
    conditions = [course_blocks.c.room == room, course_blocks.c.weekday == weekday, course_blocks.c.is_active == 1]
    if semester: conditions.append(course_blocks.c.semester == semester)
    stmt = select(course_blocks.c.semester, course_blocks.c.room, course_blocks.c.weekday,
        course_blocks.c.start_time, course_blocks.c.end_time, course_blocks.c.course_name,
        course_blocks.c.teacher).where(and_(*conditions)).order_by(course_blocks.c.start_time)
    with engine.connect() as conn:
        return rows_to_dicts(conn.execute(stmt))

def check_booking_conflict(booking_date, room, start_time, end_time, exclude_booking_id=None):
    for course in get_course_blocks(booking_date, room):
        if start_time < course["end_time"] and end_time > course["start_time"]:
            return {"type":"course", "detail":f'{course["course_name"]} {course["start_time"]}～{course["end_time"]}'}
    conditions = [bookings.c.booking_date == booking_date, bookings.c.room == room,
        bookings.c.status == "有效", start_time < bookings.c.end_time, end_time > bookings.c.start_time]
    if exclude_booking_id: conditions.append(bookings.c.booking_id != exclude_booking_id)
    stmt = select(bookings.c.booking_id, bookings.c.start_time, bookings.c.end_time).where(and_(*conditions)).limit(1)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
    if row:
        m = row._mapping; return {"type":"booking", "detail":f'{m["booking_id"]} {m["start_time"]}～{m["end_time"]}'}
    return None

def create_booking(booking_date, room, start_time, end_time, applicant_type, applicant_name, identification_code, phone, email, reason):
    with engine.begin() as conn:
        result = conn.execute(insert(bookings).values(booking_id=None, booking_date=booking_date, room=room,
            start_time=start_time, end_time=end_time, applicant_type=applicant_type,
            applicant_name=applicant_name, identification_code=identification_code, phone=phone,
            email=email, reason=reason, status="有效", created_at=now_text()))
        row_id = result.inserted_primary_key[0]
        booking_id = f"AU-PSY-{booking_date.replace('-', '')}-{int(row_id):05d}"
        conn.execute(update(bookings).where(bookings.c.id == row_id).values(booking_id=booking_id))
    log_action("CREATE", "booking", booking_id, f"{room} {start_time}-{end_time}")
    return booking_id

def get_all_bookings():
    stmt = select(bookings).order_by(bookings.c.booking_date.desc(), bookings.c.start_time.desc())
    with engine.connect() as conn: return rows_to_dicts(conn.execute(stmt))

def get_booking_by_id(booking_id):
    with engine.connect() as conn:
        row = conn.execute(select(bookings).where(bookings.c.booking_id == booking_id)).first()
    return dict(row._mapping) if row else None

def update_booking(booking_id, booking_date, room, start_time, end_time, reason):
    with engine.begin() as conn:
        conn.execute(update(bookings).where(and_(bookings.c.booking_id == booking_id, bookings.c.status == "有效")).values(
            booking_date=booking_date, room=room, start_time=start_time, end_time=end_time,
            reason=reason, updated_at=now_text()))
    log_action("UPDATE", "booking", booking_id, f"{room} {start_time}-{end_time}")

def cancel_booking(booking_id, cancel_reason):
    with engine.begin() as conn:
        conn.execute(update(bookings).where(and_(bookings.c.booking_id == booking_id, bookings.c.status == "有效")).values(
            status="已取消", cancel_reason=cancel_reason, cancelled_at=now_text()))
    log_action("CANCEL", "booking", booking_id, cancel_reason)

def get_dashboard_counts():
    with engine.connect() as conn:
        teachers = conn.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type=="教師", authorized_users.c.status=="啟用"))).scalar_one()
        students = conn.execute(select(func.count()).select_from(authorized_users).where(and_(authorized_users.c.user_type=="學生", authorized_users.c.status=="啟用"))).scalar_one()
        active = conn.execute(select(func.count()).select_from(bookings).where(bookings.c.status=="有效")).scalar_one()
    return {"teachers":teachers, "students":students, "active_bookings":active}

def get_audit_logs(limit=1000):
    safe_limit = max(1, min(int(limit), 5000))
    stmt = select(audit_logs).order_by(audit_logs.c.id.desc()).limit(safe_limit)
    with engine.connect() as conn: return rows_to_dicts(conn.execute(stmt))
