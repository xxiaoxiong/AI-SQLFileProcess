import os
import re
import time
import difflib
import concurrent.futures
import threading

from scanner import scan_java_files
from model_client import call_model
from db import (
    insert_file_record, update_file_processing,
    update_file_completed, update_file_failed
)

_lock = threading.Lock()


def _log(log_callback, msg):
    with _lock:
        ts = time.strftime('%H:%M:%S')
        log_callback(f"[{ts}] {msg}")


def _fmt_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    return f"{size_bytes / (1024*1024):.1f}MB"


def verify_code(original, fixed):
    """Basic fidelity check: class names in original must all appear in fixed."""
    orig_classes = set(re.findall(r'\bclass\s+(\w+)', original))
    if not orig_classes:
        return True
    fixed_classes = set(re.findall(r'\bclass\s+(\w+)', fixed))
    return orig_classes.issubset(fixed_classes)


def count_changes(original, fixed):
    """Estimate SQL injection fix count by difflib hunk count."""
    orig_lines = original.splitlines()
    fixed_lines = fixed.splitlines()
    hunks = sum(
        1 for tag, *_ in difflib.SequenceMatcher(None, orig_lines, fixed_lines).get_opcodes()
        if tag in ('replace', 'insert', 'delete')
    )
    return hunks


def process_single_file(file_info, source_dir, target_dir, config, db_path,
                        session_id, stop_event, log_callback, file_idx, file_total):
    abs_path, rel_path = file_info
    tag = f"[{file_idx}/{file_total}]"

    if stop_event.is_set():
        return

    target_path = os.path.join(target_dir, rel_path)
    record_id = insert_file_record(db_path, session_id, abs_path, target_path)
    start_time = time.time()

    try:
        update_file_processing(db_path, record_id)

        file_size = os.path.getsize(abs_path)
        _log(log_callback, f"{tag} 开始处理: {rel_path} ({_fmt_size(file_size)})")

        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            original_code = f.read()

        line_count = original_code.count('\n') + 1
        _log(log_callback, f"{tag} 读取完成: {line_count} 行, 准备调用模型...")

        fixed_code = None
        last_error = None
        for attempt in range(3):
            if stop_event.is_set():
                update_file_failed(db_path, record_id, "任务已停止")
                return
            try:
                model_start = time.time()
                _log(log_callback, f"{tag} 模型调用中... {rel_path}" +
                     (f" (第{attempt+1}次重试)" if attempt > 0 else ""))
                fixed_code = call_model(original_code, config)
                model_elapsed = time.time() - model_start
                _log(log_callback, f"{tag} 模型响应完成: {rel_path} | 模型耗时: {model_elapsed:.1f}s | 返回{len(fixed_code)}字符")
                break
            except Exception as e:
                last_error = str(e)
                if attempt < 2:
                    wait_sec = 3 * (attempt + 1)
                    _log(log_callback, f"{tag} [重试 {attempt+1}/2] {rel_path}: {last_error}，{wait_sec}s后重试")
                    time.sleep(wait_sec)

        if fixed_code is None:
            raise Exception(f"模型调用失败（已重试2次）: {last_error}")

        if not verify_code(original_code, fixed_code):
            raise Exception("保真校验失败：类名被修改，已丢弃模型输出")

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(fixed_code)

        vuln_count = count_changes(original_code, fixed_code)
        elapsed = time.time() - start_time
        update_file_completed(db_path, record_id, vuln_count, elapsed)
        _log(log_callback, f"{tag} [完成] {rel_path} | 修复处数: {vuln_count} | 总耗时: {elapsed:.1f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        update_file_failed(db_path, record_id, str(e))
        _log(log_callback, f"{tag} [失败] {rel_path}: {e}")


def start_processing(source_dir, session_id, config, db_path,
                     stop_event, log_callback, on_finish):
    try:
        _log(log_callback, f"[扫描] 开始扫描目录: {source_dir}")
        files = scan_java_files(source_dir, log_callback=log_callback)

        if not files:
            _log(log_callback, "[扫描] 未找到任何 .java 文件，任务结束")
            return

        total_size = 0
        for abs_p, _ in files:
            try:
                total_size += os.path.getsize(abs_p)
            except OSError:
                pass
        _log(log_callback, f"[扫描] 共找到 {len(files)} 个 Java 文件，总大小: {_fmt_size(total_size)}")

        source_dir_abs = os.path.abspath(source_dir)
        source_name = os.path.basename(source_dir_abs.rstrip('/\\').rstrip('\\'))
        parent_dir = os.path.dirname(source_dir_abs.rstrip('/\\').rstrip('\\'))
        target_dir = os.path.join(parent_dir, source_name + '_sql_fixed')

        _log(log_callback, f"[输出] 修复目录: {target_dir}")

        max_workers = max(1, int(config.get('concurrency', 4)))
        _log(log_callback, f"[启动] 并发线程数: {max_workers}，模型: {config.get('model_name', 'N/A')}")

        file_total = len(files)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    fi, source_dir_abs, target_dir, config,
                    db_path, session_id, stop_event, log_callback,
                    idx + 1, file_total
                ): fi[1]
                for idx, fi in enumerate(files)
            }
            for future in concurrent.futures.as_completed(futures):
                rel = futures[future]
                try:
                    future.result()
                except Exception as e:
                    _log(log_callback, f"[异常] {rel}: {e}")

        if stop_event.is_set():
            _log(log_callback, "[停止] 任务已手动停止")
        else:
            _log(log_callback, f"[完成] 全部文件处理完毕，输出目录: {target_dir}")

    except Exception as e:
        _log(log_callback, f"[错误] 处理过程异常: {e}")
    finally:
        on_finish()
