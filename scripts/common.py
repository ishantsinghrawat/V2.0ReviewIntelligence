from __future__ import annotations
import hashlib, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

def load_settings():
    return json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))

def load_json(path, default=None):
    p = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not p.exists(): return [] if default is None else default
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return [] if default is None else default

def save_json(path, obj):
    p = ROOT / path if not Path(path).is_absolute() else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def stable_review_id(r):
    existing = str(r.get("review_id") or "").strip()
    if existing: return existing
    raw = "|".join(str(r.get(k) or "").strip() for k in ["source","review_date","user_name","review_title","review"])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def utc_today():
    return datetime.now(timezone.utc).date()
