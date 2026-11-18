"""Tiện ích kết nối MySQL và chạy file script SQL.

Cấu hình qua biến môi trường (hoặc file .env cùng thư mục gốc dự án):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, SOURCE_DB, DW_DB
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ROOT_DIR = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT_DIR / "sql"
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"


def _load_dotenv() -> None:
    """Đọc file .env đơn giản (KEY=VALUE) nếu có, không ghi đè biến đã đặt."""
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned_val = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned_val)


_load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
SOURCE_DB = "phone_source"
DW_DB = "phone_dw"


def get_engine(database: str | None = None) -> Engine:
    """Tạo SQLAlchemy engine tới MySQL (driver PyMySQL, utf8mb4)."""
    url = (
        f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/"
        f"{database or ''}?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True)


def split_sql_script(script: str) -> list[str]:
    """Tách script SQL thành từng câu lệnh, hỗ trợ chỉ thị DELIMITER (cho stored procedure).

    Quy ước: dòng bắt đầu bằng '--' là chú thích và bị bỏ qua; mỗi câu lệnh kết thúc
    bằng delimiter hiện hành ở cuối dòng.
    """
    statements: list[str] = []
    delimiter = ";"
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not buffer and (not stripped or stripped.startswith("--")):
            continue
        if stripped.startswith("--"):
            continue
        if stripped.upper().startswith("DELIMITER "):
            delimiter = stripped.split(None, 1)[1]
            continue
        buffer.append(line)
        if stripped.endswith(delimiter):
            statement = "\n".join(buffer).rstrip()
            statement = statement[: -len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def run_sql_file(engine: Engine, path: Path | str, verbose: bool = False) -> int:
    """Thực thi toàn bộ câu lệnh trong một file .sql. Trả về số câu lệnh đã chạy."""
    path = Path(path)
    statements = split_sql_script(path.read_text(encoding="utf-8"))
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        for stmt in statements:
            if verbose:
                print("   >", stmt.splitlines()[0][:100])
            cursor.execute(stmt)
            # Đọc bỏ các result set (nếu câu lệnh là SELECT) để giải phóng kết nối
            while True:
                if cursor.description is not None:
                    cursor.fetchall()
                if not cursor.nextset():
                    break
        raw.commit()
        cursor.close()
    finally:
        raw.close()
    return len(statements)


def call_procedure(engine: Engine, name: str, args: tuple = ()) -> list[dict]:
    """Gọi stored procedure, trả về result set đầu tiên dưới dạng list[dict]."""
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        placeholders = ", ".join(["%s"] * len(args))
        cursor.execute(f"CALL {name}({placeholders})", args)
        rows: list[dict] = []
        first = True
        while True:
            if cursor.description is not None:
                cols = [c[0] for c in cursor.description]
                data = cursor.fetchall()
                if first:
                    rows = [dict(zip(cols, r)) for r in data]
                    first = False
            if not cursor.nextset():
                break
        raw.commit()
        cursor.close()
        return rows
    finally:
        raw.close()

