import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULT_CONFIG = {
    "api_url": "http://10.158.64.11:30888/one-api/v1/chat/completions",
    "api_key": "sk-KbMJu2lFFUt3Nkgz66A501C2764e474595F40e615eCd4b4e",
    "model_name": "gen-studio-DeepSeek-R1-0528-AaTW",
    "timeout": 120,
    "concurrency": 4,
    "source_dir": ""
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            config = {**DEFAULT_CONFIG, **saved}
            return config
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    merged = {**load_config(), **config}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
