import os
import sys
import socket
import threading
import time
import webbrowser


# ─── Path helpers (PyInstaller-aware) ───────────────────────────────────────

def get_base_dir():
    """Writable directory: config.json and sql_fix_log.db live here."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """Read-only resource directory: bundled templates live here."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


# ─── Port utilities ──────────────────────────────────────────────────────────

def find_free_port(start=5000):
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def wait_server(port, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(port):
            return True
        time.sleep(0.25)
    return False


# ─── Flask runner ────────────────────────────────────────────────────────────

def _run_flask(port):
    from app import app as flask_app
    flask_app.run(
        host='127.0.0.1',
        port=port,
        debug=False,
        threaded=True,
        use_reloader=False,
    )


# ─── Tray icon ───────────────────────────────────────────────────────────────

def _make_icon_image():
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new('RGB', (size, size), '#1e3a5f')
    d = ImageDraw.Draw(img)
    for i, y in enumerate([18, 30, 42]):
        bar_width = [44, 36, 28][i]
        d.rectangle([10, y - 3, 10 + bar_width, y + 3], fill='white')
    d.ellipse([40, 4, 58, 22], fill='#4fc3f7')
    return img


def _run_tray(url):
    try:
        import pystray
        img = _make_icon_image()

        def on_open(icon, item):
            webbrowser.open(url)

        def on_exit(icon, item):
            icon.stop()
            os._exit(0)

        icon = pystray.Icon(
            'SQLFixTool',
            img,
            'SQL注入修复工具',
            pystray.Menu(
                pystray.MenuItem('打开界面', on_open, default=True),
                pystray.MenuItem('退出程序', on_exit),
            ),
        )
        icon.run()
    except Exception:
        _run_tkinter_fallback(url)


def _run_tkinter_fallback(url):
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title('SQL注入修复工具')
        root.geometry('320x130')
        root.resizable(False, False)

        tk.Label(
            root, text='SQL注入修复工具正在运行中',
            font=('微软雅黑', 11, 'bold'), pady=12
        ).pack()
        tk.Label(
            root, text='关闭此窗口将退出程序',
            font=('微软雅黑', 9), fg='gray'
        ).pack()

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text='打开界面', width=14,
                   command=lambda: webbrowser.open(url)).pack(side='left', padx=6)
        ttk.Button(btn_frame, text='退出程序', width=14,
                   command=lambda: os._exit(0)).pack(side='left', padx=6)

        root.protocol('WM_DELETE_WINDOW', lambda: os._exit(0))
        root.mainloop()
    except Exception:
        threading.Event().wait()


# ─── Main entry ──────────────────────────────────────────────────────────────

def run_app():
    base_dir = get_base_dir()
    resource_dir = get_resource_dir()

    os.environ['APP_BASE_DIR'] = base_dir
    os.environ['APP_RESOURCE_DIR'] = resource_dir

    if is_port_open(5000):
        webbrowser.open('http://127.0.0.1:5000')
        sys.exit(0)

    port = find_free_port(5000)
    url = f'http://127.0.0.1:{port}'

    t = threading.Thread(target=_run_flask, args=(port,), daemon=True)
    t.start()

    wait_server(port)
    webbrowser.open(url)

    _run_tray(url)


if __name__ == '__main__':
    run_app()
