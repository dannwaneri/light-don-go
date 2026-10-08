"""Rules compute every fact. The model only phrases them."""
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Port Harcourt rainy season: almost every hour has a 50%+ chance, so 50% would keep
# everyone indoors all day. "Wet" = real expected rain, or a high chance.
WET_PROB = 70
WET_MM = 0.5


def sun_times(lat, lon, day):
    """NOAA general solar position formulas. Returns (sunrise, sunset) as UTC datetimes."""
    doy = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (doy - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat_r = math.radians(lat)
    cos_ha = (math.cos(math.radians(90.833)) / (math.cos(lat_r) * math.cos(decl))
              - math.tan(lat_r) * math.tan(decl))
    ha = math.degrees(math.acos(max(-1.0, min(1.0, cos_ha))))
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    rise = midnight + timedelta(minutes=720 - 4 * (lon + ha) - eqtime)
    sset = midnight + timedelta(minutes=720 - 4 * (lon - ha) - eqtime)
    return rise, sset


def _wet(h):
    return (h["precip_prob"] or 0) >= WET_PROB or (h["precip_mm"] or 0) >= WET_MM


@dataclass
class Facts:
    now: datetime                       # local, tz-aware
    battery_pct: int
    sunset: datetime                    # local
    after_sunset: bool
    forecast_ok: bool
    forecast_age_min: int | None
    is_raining: bool
    rain_at: datetime | None            # local, first wet hour after now
    temp_c: float | None
    naira_saved_per_hour: int | None
    go_until: datetime | None           # earlier of rain_at and sunset; None if raining or dark
    go_reason: str | None               # "rain" | "sunset"
    minutes_left: int | None
    activity: str = ""
    category: str = ""
    extra: dict = field(default_factory=dict)

    def model_view(self, place):
        """The only facts the model sees: no numbers at all (split design, 2026-10-08)."""
        if self.is_raining:
            situation = "raining now"
        elif self.after_sunset:
            situation = "after dark"
        else:
            situation = "dry daylight"
        return {"place": place, "situation": situation, "activity": self.activity}


def build(now_utc, forecast, battery_pct, cfg):
    tz = cfg.tz
    now = now_utc.astimezone(tz)
    _, sset = sun_times(cfg.lat, cfg.lon, now.date())
    sunset = sset.astimezone(tz)
    after_sunset = now >= sunset

    is_raining, rain_at, temp_c = False, None, None
    if forecast is not None:
        hours = sorted(forecast["hours"], key=lambda h: h["time"])
        current = [h for h in hours if h["time"] <= now_utc < h["time"] + timedelta(hours=1)]
        if current:
            is_raining = _wet(current[0])
            temp_c = current[0]["temp_c"]
        for h in hours:
            if h["time"] > now_utc and _wet(h):
                rain_at = h["time"].astimezone(tz)
                break

    go_until, go_reason = None, None
    if not is_raining and not after_sunset:
        go_until, go_reason = sunset, "sunset"
        if rain_at is not None and rain_at < sunset:
            go_until, go_reason = rain_at, "rain"
    minutes_left = None if go_until is None else int((go_until - now).total_seconds() // 60)

    return Facts(
        now=now, battery_pct=int(battery_pct), sunset=sunset, after_sunset=after_sunset,
        forecast_ok=forecast is not None,
        forecast_age_min=None if forecast is None else forecast["age_min"],
        is_raining=is_raining, rain_at=rain_at, temp_c=temp_c,
        naira_saved_per_hour=cfg.naira_saved_per_hour,
        go_until=go_until, go_reason=go_reason, minutes_left=minutes_left,
    )
