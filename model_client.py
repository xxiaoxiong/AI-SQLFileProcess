import re
import requests

PROMPT_TEMPLATE = """【绝对强制约束，必须100%遵守】
1. 仅允许修复代码中的SQL注入漏洞，禁止修改任何其他内容！
2. 禁止改动：类名、方法名、变量名、包名、注释、入参、返回值、业务逻辑！
3. 禁止新增/删除代码、禁止格式化、禁止重构、禁止优化非注入代码！
4. 修复规则（仅允许以下操作）：
   - JDBC：Statement字符串拼接SQL → 替换为PreparedStatement预编译
   - MyBatis：${{}}变量 → 替换为#{{}}预编译参数
   - 保留原有SQL逻辑，仅修改参数传递方式
5. 必须返回【完整可运行的Java代码】，不要解释、不要摘要、不要额外文字，仅返回代码！

【任务】
检测并修复以下Java代码中的所有SQL注入漏洞，其余代码一字不差保留：

{code}"""


def call_model(code, config):
    """
    Call LAN model API to detect and fix SQL injection in Java code.
    Returns fixed code string.
    Raises exception on failure.
    """
    api_url = config.get('api_url', '').strip()
    api_key = config.get('api_key', '').strip()
    model_name = config.get('model_name', '').strip()
    timeout = int(config.get('timeout', 120))

    if not api_url or not api_key or not model_name:
        raise ValueError("API地址、API Key 或模型名称未配置")

    prompt = PROMPT_TEMPLATE.format(code=code)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    payload = {
        'model': model_name,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.1,
        'max_tokens': 8192
    }

    resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    if not resp.ok:
        try:
            err_body = resp.json()
        except Exception:
            err_body = resp.text[:300]
        raise RuntimeError(f"HTTP {resp.status_code}: {err_body}")
    resp.raise_for_status()

    data = resp.json()
    content = data['choices'][0]['message']['content']
    fixed = extract_code(content)

    if not is_pure_java_code(fixed):
        raise ValueError("模型返回包含非代码说明文字，已拒绝本次输出")

    return fixed


def extract_code(text):
    """Extract Java code from model response and strip markdown wrappers."""
    text = text.strip()

    # Handle <think>...</think> reasoning blocks (DeepSeek-R1 style)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # Prefer fenced code blocks if present
    fenced_blocks = re.findall(r'```(?:java)?\s*\n?(.*?)```', text, flags=re.DOTALL)
    if fenced_blocks:
        for block in fenced_blocks:
            block = block.strip()
            if is_pure_java_code(block):
                return block
        return fenced_blocks[0].strip()

    # No fence: cut possible prose before Java start
    start = re.search(r'(?m)^\s*(package\s+[\w\.]+\s*;|import\s+[\w\.\*]+\s*;|(public\s+)?(class|interface|enum)\s+\w+)', text)
    if start:
        return text[start.start():].strip()

    return text


def is_pure_java_code(text):
    """Reject obvious markdown/explanation and keep only Java-looking output."""
    if not text:
        return False

    stripped = text.strip()

    # Markdown fences should not exist after extraction
    if '```' in stripped:
        return False

    # Must look like a Java source file
    has_java_structure = bool(re.search(r'(?m)^\s*(package\s+[\w\.]+\s*;|import\s+[\w\.\*]+\s*;|(public\s+)?(class|interface|enum)\s+\w+)', stripped))
    if not has_java_structure:
        return False

    # Common explanation markers at beginning
    head = '\n'.join([ln.strip() for ln in stripped.splitlines()[:12] if ln.strip()])
    bad_markers = (
        '以下是', '说明', '解释', '修改点', '总结',
        'Here is', 'Explanation', 'Summary',
        '#', '- ', '* '
    )
    return not any(marker in head for marker in bad_markers)
