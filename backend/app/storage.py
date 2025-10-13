import json, os
from typing import Dict, Any
from .config import DATA_DIR

def _path(key_hex: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f"{key_hex}.json")

def save_cache(key_hex: str, payload: Dict[str, Any]) -> None:
    with open(_path(key_hex), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def load_cache(key_hex: str) -> Dict[str, Any]:
    p = _path(key_hex)
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
