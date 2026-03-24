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
    return extract_code(content)


def extract_code(text):
    """Strip markdown code fences from model response."""
    text = text.strip()

    # Handle <think>...</think> reasoning blocks (DeepSeek-R1 style)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # Match ```java ... ``` or ``` ... ```
    match = re.search(r'```(?:java)?\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Match ``` at start of line
    match = re.search(r'```(?:java)?(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text
