from datetime import date, datetime, timedelta, timezone

from light_don_go import facts, picker
from light_don_go.config import Config
from conftest import WAT, forecast_from

CFG = Config()


def utc(h, m=0, day=8):
    return datetime(2026, 10, day, h, m, tzinfo=WAT).astimezone(timezone.utc)


def test_port_harcourt_sunset_matches_published():
    # Published 2026-10-07: Open-Meteo 18:21 WAT, sunrise-sunset.org 17:22:09 UTC (18:22 WAT)
    _, sset = facts.sun_times(CFG.lat, CFG.lon, date(2026, 10, 7))
    published = datetime(2026, 10, 7, 17, 22, 9, tzinfo=timezone.utc)
    assert abs((sset - published).total_seconds()) <= 180


def test_stale_forecast_gives_no_rain_or_temp_and_sunset_window():
    f = facts.build(utc(16, 0), None, 50, CFG)
    assert f.forecast_ok is False and f.rain_at is None and f.temp_c is None
    assert f.go_reason == "sunset" and 135 <= f.minutes_left <= 145


def test_rain_before_sunset_sets_window_to_rain():
    fc = forecast_from([("2026-10-08T15:00", 10, 0.0, 29), ("2026-10-08T16:00", 20, 0.0, 28),
                        ("2026-10-08T17:00", 90, 2.0, 26)], "x")
    f = facts.build(utc(16, 10), fc, 50, CFG)          # 15:10 UTC
    assert f.is_raining is False
    assert f.go_reason == "rain" and f"{f.go_until:%H:%M}" == "18:00" and f.minutes_left == 110


def test_raining_now_has_no_window():
    fc = forecast_from([("2026-10-08T15:00", 95, 3.0, 25)], "x")
    f = facts.build(utc(16, 30), fc, 50, CFG)
    assert f.is_raining and f.go_until is None and f.minutes_left is None


def test_high_chance_but_no_rain_is_not_wet_below_70():
    fc = forecast_from([("2026-10-08T15:00", 55, 0.1, 27)], "x")
    assert facts.build(utc(16, 30), fc, 50, CFG).is_raining is False


def test_after_sunset_always_picks_near_home():
    f = facts.build(utc(19, 30), None, 50, CFG)
    assert f.after_sunset and f.go_until is None
    for oid in range(20):
        picker.pick(f, oid)
        assert f.activity in picker.AFTER_DARK


def test_model_view_hides_time_now_and_later_limit():
    fc = forecast_from([("2026-10-08T17:00", 90, 2.0, 26)], "x")
    f = facts.build(utc(16, 10), fc, 50, CFG)
    picker.pick(f, 0)
    v = f.model_view("Port Harcourt")
    assert set(v) == {"place", "situation", "activity"} and v["situation"] == "dry daylight"


def test_no_activity_contains_a_digit():
    for pool in (picker.DAY_DRY, picker.RAINING, picker.AFTER_DARK):
        assert not any(ch.isdigit() for a in pool for ch in a)
