"""Save the hourly forecast while power and internet are on; read it back offline."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_AGE = timedelta(hours=6)
URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
       "&hourly=precipitation_probability,precipitation,temperature_2m"
       "&forecast_days=2&timezone=GMT")


def _fetch(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def parse(raw, fetched_at):
    h = raw["hourly"]
    hours = []
    for t, prob, mm, temp in zip(h["time"], h["precipitation_probability"],
                                 h["precipitation"], h["temperature_2m"]):
        hours.append({"time": t, "precip_prob": prob, "precip_mm": mm, "temp_c": temp})
    return {"fetched_at": fetched_at.astimezone(timezone.utc).isoformat(), "hours": hours}


def refresh(cfg, path="cache/forecast.json", fetch=_fetch, now=None):
    """Fetch and save. Never raises; returns False and keeps the old cache on any error."""
    now = now or datetime.now(timezone.utc)
    try:
        raw = fetch(URL.format(lat=cfg.lat, lon=cfg.lon))
        data = parse(raw, now)
        if not data["hours"]:
            return False
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, p)
        return True
    except Exception:
        return False


def load(path, now):
    """Return the cached forecast with datetimes, or None if missing, broken, or older than 6 h."""
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        fetched = datetime.fromisoformat(data["fetched_at"])
        hours = [dict(h, time=datetime.fromisoformat(h["time"]).replace(tzinfo=timezone.utc))
                 for h in data["hours"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    age = now - fetched
    if age > MAX_AGE or age < -timedelta(minutes=5):
        return None
    return {"fetched_at": fetched, "age_min": int(age.total_seconds() // 60), "hours": hours}


def age_minutes(path, now):
    f = load(path, now)
    return None if f is None else f["age_min"]
