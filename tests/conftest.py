import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from light_don_go.config import Config
from light_don_go.facts import Facts

WAT = timezone(timedelta(hours=1))
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cfg():
    return Config()


def make_facts(minutes_left=75, go_until="18:21", battery=41, naira=1500,
               raining=False, after_sunset=False, reason="sunset"):
    now = datetime(2026, 10, 8, 17, 6, tzinfo=WAT)
    gu = None
    if go_until is not None:
        h, m = map(int, go_until.split(":"))
        gu = now.replace(hour=h, minute=m)
    return Facts(now=now, battery_pct=battery, sunset=now.replace(hour=18, minute=20),
                 after_sunset=after_sunset, forecast_ok=True, forecast_age_min=30,
                 is_raining=raining, rain_at=None, temp_c=28.0, naira_saved_per_hour=naira,
                 go_until=gu, go_reason=None if gu is None else reason,
                 minutes_left=minutes_left, activity="walk to the junction and buy roasted plantain and fish")


@pytest.fixture
def facts():
    return make_facts()


def forecast_from(hours, fetched_at):
    """hours: list of (utc_iso_hour, prob, mm, temp)."""
    return {"fetched_at": fetched_at, "age_min": 30,
            "hours": [{"time": datetime.fromisoformat(t).replace(tzinfo=timezone.utc),
                       "precip_prob": p, "precip_mm": mm, "temp_c": tc} for t, p, mm, tc in hours]}


@pytest.fixture
def open_meteo_raw():
    return json.loads((FIXTURES / "open_meteo_ph.json").read_text(encoding="utf-8"))
