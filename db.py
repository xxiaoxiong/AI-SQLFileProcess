import sqlite3
import threading
import queue
from datetime import datetime


# ---------------------------------------------------------------------------
# Single-writer thread: all INSERT / UPDATE / DELETE go through _write_queue
# so concurrent worker threads never fight over the SQLite write lock.
# ---------------------------------------------------------------------------
_write_queue = queue.Queue()
_writer_thread = None
_writer_started = False
_writer_lock = threading.Lock()
_db_path_global = None


def _writer_loop():
    """Drain the write queue and execute statements serially."""
    conn = sqlite3.connect(_db_path_global, check_same_thread=False, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    while True:
        item = _write_queue.get()
        if item is None:          # poison pill
            conn.close()
            break
        sql, params, result_event, result_holder = item
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            result_holder['lastrowid'] = cur.lastrowid
            result_holder['error'] = None
        except Exception as e:
            result_holder['error'] = e
        finally:
            result_event.set()


def _ensure_writer():
    global _writer_thread, _writer_started
    with _writer_lock:
        if not _writer_started:
            _writer_started = True
            _writer_thread = threading.Thread(target=_writer_loop, daemon=True)
            _writer_thread.start()


def _exec_write(sql, params=()):
    """Submit a write to the single-writer thread and wait for the result."""
    _ensure_writer()
    result = {}
    evt = threading.Event()
    _write_queue.put((sql, params, evt, result))
    evt.wait()
    if result.get('error'):
        raise result['error']
    return result.get('lastrowid')


def _get_read_conn(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(db_path):
    global _db_path_global
    _db_path_global = db_path
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
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
    conn.close()
    _ensure_writer()


def insert_file_record(db_path, session_id, source_file, target_file):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return _exec_write(
        """INSERT INTO file_process_log
           (session_id, source_file, target_file, process_status, create_time, update_time)
           VALUES (?, ?, ?, '待处理', ?, ?)""",
        (session_id, source_file, target_file, now, now)
    )


def update_file_processing(db_path, record_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _exec_write(
        "UPDATE file_process_log SET process_status='处理中', update_time=? WHERE id=?",
        (now, record_id)
    )


def update_file_completed(db_path, record_id, vuln_count, process_time):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _exec_write(
        """UPDATE file_process_log
           SET process_status='已完成', vuln_count=?, process_time=?, update_time=?
           WHERE id=?""",
        (vuln_count, round(process_time, 2), now, record_id)
    )


def update_file_failed(db_path, record_id, error_msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _exec_write(
        """UPDATE file_process_log
           SET process_status='处理失败', error_msg=?, update_time=?
           WHERE id=?""",
        (str(error_msg)[:500], now, record_id)
    )


def delete_session_records(db_path, session_id):
    """Delete all records for a session."""
    _exec_write(
        "DELETE FROM file_process_log WHERE session_id=?",
        (session_id,)
    )


def delete_all_records(db_path):
    """Delete all records."""
    _exec_write("DELETE FROM file_process_log")


def get_session_stats(db_path, session_id):
    if not session_id:
        return {}
    with _get_read_conn(db_path) as conn:
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
    with _get_read_conn(db_path) as conn:
        rows = conn.execute(
            """SELECT id, source_file, target_file, process_status, vuln_count,
                      process_time, error_msg, create_time, update_time
               FROM file_process_log WHERE session_id=?
               ORDER BY id DESC LIMIT ?""",
            (session_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_sessions(db_path):
    with _get_read_conn(db_path) as conn:
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
