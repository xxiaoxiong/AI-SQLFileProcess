import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

args = [
    sys.executable, '-m', 'PyInstaller',
    '--onefile',
    '--noconsole',
    '--name', 'SQL注入修复工具',
    '--add-data', 'templates;templates',
    '--collect-all', 'flask',
    '--collect-all', 'jinja2',
    '--collect-all', 'werkzeug',
    '--collect-all', 'click',
    '--hidden-import', 'pystray',
    '--hidden-import', 'pystray._win32',
    '--collect-all', 'PIL',
    '--hidden-import', 'requests',
    '--hidden-import', 'urllib3',
    '--hidden-import', 'charset_normalizer',
    '--hidden-import', 'certifi',
    '--hidden-import', 'sqlite3',
    '--hidden-import', 'difflib',
    '--hidden-import', 'concurrent.futures',
    'main.py',
]

print('=' * 60)
print('  Building: SQL注入修复工具.exe')
print('  This may take 1-3 minutes on first run...')
print('=' * 60)

result = subprocess.run(args)

if result.returncode == 0:
    print()
    print('=' * 60)
    print('  Build successful!')
    print('  Output : dist\\SQL注入修复工具.exe')
    print('  Usage  : Copy the .exe to any Windows PC and double-click')
    print('  Exit   : Right-click tray icon -> 退出程序')
    print('=' * 60)
else:
    print()
    print('[ERROR] Build failed. Check the output above for details.')
    sys.exit(1)
