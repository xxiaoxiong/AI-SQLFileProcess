import os
import threading
import uuid

from flask import Flask, render_template, request, jsonify

from config_store import load_config, save_config
from db import (init_db, get_session_stats, get_session_records, get_all_sessions,
               delete_session_records, delete_all_records)
from processor import start_processing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'sql_fix_log.db')

app = Flask(__name__)
init_db(DB_PATH)

_job = {
    'running': False,
    'session_id': None,
    'stop_event': None,
    'logs': [],
    'lock': threading.Lock()
}


def _add_log(msg):
    with _job['lock']:
        _job['logs'].append(msg)
        if len(_job['logs']) > 1000:
            _job['logs'] = _job['logs'][-1000:]


def _on_finish():
    _job['running'] = False


@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)


@app.route('/api/config', methods=['GET'])
def api_get_config():
    return jsonify(load_config())


@app.route('/api/config', methods=['POST'])
def api_save_config():
    data = request.get_json(silent=True) or {}
    save_config(data)
    return jsonify({'ok': True})


@app.route('/api/start', methods=['POST'])
def api_start():
    if _job['running']:
        return jsonify({'error': '已有任务正在运行，请等待完成或手动停止'}), 400

    data = request.get_json(silent=True) or {}
    source_dir = data.get('source_dir', '').strip()
    if not source_dir:
        return jsonify({'error': '请输入源文件夹路径'}), 400
    if not os.path.isdir(source_dir):
        return jsonify({'error': f'目录不存在: {source_dir}'}), 400

    config = {**load_config(), **data}
    save_config(config)

    session_id = uuid.uuid4().hex[:8]
    stop_event = threading.Event()

    _job['running'] = True
    _job['session_id'] = session_id
    _job['stop_event'] = stop_event
    _job['logs'] = []

    thread = threading.Thread(
        target=start_processing,
        args=(source_dir, session_id, config, DB_PATH, stop_event, _add_log, _on_finish),
        daemon=True
    )
    thread.start()

    return jsonify({'ok': True, 'session_id': session_id})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    if _job['stop_event']:
        _job['stop_event'].set()
    return jsonify({'ok': True})


@app.route('/api/status', methods=['GET'])
def api_status():
    session_id = _job['session_id']
    stats = get_session_stats(DB_PATH, session_id) if session_id else {}
    with _job['lock']:
        logs = list(_job['logs'][-200:])
    return jsonify({
        'running': _job['running'],
        'session_id': session_id,
        'stats': stats,
        'logs': logs
    })


@app.route('/api/records', methods=['GET'])
def api_records():
    session_id = request.args.get('session_id') or _job['session_id']
    records = get_session_records(DB_PATH, session_id) if session_id else []
    return jsonify(records)


@app.route('/api/sessions', methods=['GET'])
def api_sessions():
    return jsonify(get_all_sessions(DB_PATH))


@app.route('/api/clear-logs', methods=['POST'])
def api_clear_logs():
    """Clear server-side in-memory logs so polling won't bring them back."""
    with _job['lock']:
        _job['logs'] = []
    return jsonify({'ok': True})


@app.route('/api/records/delete', methods=['POST'])
def api_delete_records():
    """Delete processing records. Pass session_id to delete one session, or 'all' to wipe everything."""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id', '').strip()
    if session_id == 'all':
        delete_all_records(DB_PATH)
    elif session_id:
        delete_session_records(DB_PATH, session_id)
    else:
        return jsonify({'error': '请指定 session_id 或 "all"'}), 400
    return jsonify({'ok': True})


if __name__ == '__main__':
    print("SQL注入自动检测与修复工具 启动中...")
    print("请在浏览器中访问: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
