import json
import os
import time
from datetime import datetime, timedelta, timezone

from light_don_go import forecast
from light_don_go.config import Config

NOW = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)


def test_refresh_writes_valid_cache_from_fixture(tmp_path, open_meteo_raw):
    path = tmp_path / "f.json"
    assert forecast.refresh(Config(), path, fetch=lambda url: open_meteo_raw, now=NOW)
    data = forecast.load(path, NOW + timedelta(minutes=10))
    assert data is not None and len(data["hours"]) == 48
    assert data["hours"][0]["time"].tzinfo is not None


def test_network_error_returns_false_and_keeps_old_cache(tmp_path, open_meteo_raw):
    path = tmp_path / "f.json"
    forecast.refresh(Config(), path, fetch=lambda url: open_meteo_raw, now=NOW)
    before = path.read_text(encoding="utf-8")

    def boom(url):
        raise OSError("router dead")
    assert forecast.refresh(Config(), path, fetch=boom, now=NOW) is False
    assert path.read_text(encoding="utf-8") == before


def test_load_returns_none_for_7h_old_cache(tmp_path, open_meteo_raw):
    path = tmp_path / "f.json"
    forecast.refresh(Config(), path, fetch=lambda url: open_meteo_raw, now=NOW)
    assert forecast.load(path, NOW + timedelta(hours=7)) is None


def test_load_returns_none_for_missing_or_broken(tmp_path):
    assert forecast.load(tmp_path / "missing.json", NOW) is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert forecast.load(bad, NOW) is None
