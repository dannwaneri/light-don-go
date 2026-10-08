"""Append-only JSONL log of every power event. This is the field-test evidence for the post."""
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path


def _default(o):
    if isinstance(o, datetime):
        return o.isoformat(timespec="seconds")
    if is_dataclass(o):
        return asdict(o)
    return str(o)


def append(record, path="logs/outages.jsonl"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=_default, ensure_ascii=False) + "\n")
