from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import os

_POOL: MySQLConnectionPool | None = None


def _pool() -> MySQLConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = MySQLConnectionPool(
            pool_name="saba_pool",
            pool_size=max(5, int(os.getenv("DB_POOL_SIZE", "10"))),
            pool_reset_session=True,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=8,
        )
    return _POOL


def get_connection():
    try:
        return _pool().get_connection()
    except Error as exc:
        # Reset the pool so a later request can recover from a transient DB failure.
        global _POOL
        _POOL = None
        raise RuntimeError(f"Database connection failed: {exc}") from exc


@contextmanager
def db_connection() -> Iterator:
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
