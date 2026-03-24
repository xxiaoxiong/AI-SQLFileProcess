import sqlite3
import os
from datetime import datetime


def get_conn(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path):
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_process_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT,
                source_file    TEXT,
                target_file    TEXT,
                process_status TEXT DEFAULT '待处理',
                vuln_count     INTEGER DEFAULT 0,
                process_time   REAL DEFAULT 0,
                error_msg      TEXT DEFAULT '',
                create_time    TIMESTAMP,
                update_time    TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON file_process_log(session_id)")
        conn.commit()


def insert_file_record(db_path, session_id, source_file, target_file):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_conn(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO file_process_log
               (session_id, source_file, target_file, process_status, create_time, update_time)
               VALUES (?, ?, ?, '待处理', ?, ?)""",
            (session_id, source_file, target_file, now, now)
        )
        conn.commit()
        return cur.lastrowid


def update_file_processing(db_path, record_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE file_process_log SET process_status='处理中', update_time=? WHERE id=?",
            (now, record_id)
        )
        conn.commit()


def update_file_completed(db_path, record_id, vuln_count, process_time):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_conn(db_path) as conn:
        conn.execute(
            """UPDATE file_process_log
               SET process_status='已完成', vuln_count=?, process_time=?, update_time=?
               WHERE id=?""",
            (vuln_count, round(process_time, 2), now, record_id)
        )
        conn.commit()


def update_file_failed(db_path, record_id, error_msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_conn(db_path) as conn:
        conn.execute(
            """UPDATE file_process_log
               SET process_status='处理失败', error_msg=?, update_time=?
               WHERE id=?""",
            (str(error_msg)[:500], now, record_id)
        )
        conn.commit()


def get_session_stats(db_path, session_id):
    if not session_id:
        return {}
    with get_conn(db_path) as conn:
        row = conn.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN process_status='待处理' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN process_status='处理中' THEN 1 ELSE 0 END) as processing,
                SUM(CASE WHEN process_status='已完成' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN process_status='处理失败' THEN 1 ELSE 0 END) as failed,
                SUM(vuln_count) as total_vulns
               FROM file_process_log WHERE session_id=?""",
            (session_id,)
        ).fetchone()
        return dict(row) if row else {}


def get_session_records(db_path, session_id, limit=200):
    if not session_id:
        return []
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """SELECT id, source_file, target_file, process_status, vuln_count,
                      process_time, error_msg, create_time, update_time
               FROM file_process_log WHERE session_id=?
               ORDER BY id DESC LIMIT ?""",
            (session_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_sessions(db_path):
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """SELECT session_id,
                      MIN(create_time) as start_time,
                      COUNT(*) as total,
                      SUM(CASE WHEN process_status='已完成' THEN 1 ELSE 0 END) as completed,
                      SUM(CASE WHEN process_status='处理失败' THEN 1 ELSE 0 END) as failed,
                      SUM(vuln_count) as total_vulns
               FROM file_process_log
               GROUP BY session_id
               ORDER BY start_time DESC
               LIMIT 20""",
        ).fetchall()
        return [dict(r) for r in rows]
