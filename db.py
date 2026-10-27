import sqlite3

from config import settings


def get_connection() -> sqlite3.Connection:
    """Direct connection for startup/init code. Not for routes."""
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables on startup. Called by app.py's lifespan."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT    NOT NULL UNIQUE,
                hashed_pw  TEXT    NOT NULL,
                role       TEXT    NOT NULL DEFAULT 'viewer',
                created_at TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                mrn         TEXT    NOT NULL UNIQUE,
                name        TEXT    NOT NULL,
                age         INTEGER NOT NULL,
                ward        TEXT    NOT NULL,
                blood_group TEXT    NOT NULL,
                contact     TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT    NOT NULL,
                specialization TEXT    NOT NULL,
                license_no     TEXT    NOT NULL UNIQUE,
                department     TEXT    NOT NULL,
                contact        TEXT,
                available      INTEGER NOT NULL DEFAULT 1,
                created_at     TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id       INTEGER NOT NULL
                                 REFERENCES patients(patient_id),
                doctor_id        INTEGER NOT NULL
                                 REFERENCES doctors(doctor_id),
                appointment_date TEXT    NOT NULL,
                appointment_time TEXT    NOT NULL DEFAULT '10:00',
                status           TEXT    NOT NULL DEFAULT 'scheduled',
                notes            TEXT             DEFAULT '',
                diagnosis        TEXT             DEFAULT '',
                created_at       TEXT             DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def get_db():
    """
    FastAPI dependency: yields one SQLite connection per request.

    check_same_thread=False: get_db() is a sync generator, so FastAPI
    runs it in a worker thread; the connection is then handed to your
    (async) route, which runs on the event loop thread. Required, or
    sqlite3 raises "objects created in a thread can only be used in
    that same thread".
    """
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
