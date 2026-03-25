import os
import sys


def _long_path(p):
    """On Windows, prefix with \\\\?\\ to support paths longer than 260 chars."""
    if sys.platform == 'win32':
        p = os.path.abspath(p)
        if not p.startswith('\\\\?\\'):
            p = '\\\\?\\' + p
    return p


def scan_java_files(source_dir, log_callback=None):
    """
    Recursively scan source_dir for .java files.
    Returns list of (abs_path, rel_path) tuples.
    rel_path is relative to source_dir (used to replicate directory structure).
    """
    source_dir = os.path.abspath(source_dir)
    long_source = _long_path(source_dir)
    results = []
    errors = []

    def _on_walk_error(err):
        errors.append(str(err))
        if log_callback:
            log_callback(f"[扫描警告] 无法访问: {err}")

    for root, dirs, files in os.walk(long_source, onerror=_on_walk_error, followlinks=False):
        for fname in files:
            if fname.lower().endswith('.java'):
                abs_path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(abs_path)
                except OSError as e:
                    if log_callback:
                        log_callback(f"[扫描警告] 无法读取文件大小: {abs_path} ({e})")
                    continue
                if size == 0:
                    continue
                # Strip the \\?\ prefix for display / rel_path calculation
                clean_abs = abs_path
                if clean_abs.startswith('\\\\?\\'):
                    clean_abs = clean_abs[4:]
                rel_path = os.path.relpath(clean_abs, source_dir)
                results.append((clean_abs, rel_path))

    return results
