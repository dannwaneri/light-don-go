"""Config loading with Port Harcourt defaults."""
import tomllib
from dataclasses import dataclass, fields, replace
from datetime import timedelta, timezone
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    lat: float = 4.8156
    lon: float = 7.0498
    place_name: str = "Port Harcourt"
    utc_offset_h: float = 1
    debounce_s: int = 30
    cooldown_min: int = 15
    poll_s: int = 5
    refresh_min: int = 30
    model: str = "gemma4:e2b-it-qat"
    model_timeout_s: int = 20
    # Ollama unloads an idle model after 5 min by default. A real outage on 2026-10-08 hit a
    # cold load on battery and timed out at 20 s. -1 keeps the model in RAM (~3.9 GB).
    model_keep_alive: int | str = -1
    ollama_url: str = "http://localhost:11434"
    takeover: bool = True          # full-screen page on an outage; toast if False
    stretch_s: int = 60
    gen_litres_per_hour: float | None = 1.0
    petrol_price_ngn: float | None = 1500

    @property
    def tz(self):
        return timezone(timedelta(hours=self.utc_offset_h))

    @property
    def naira_saved_per_hour(self):
        if self.gen_litres_per_hour is None or self.petrol_price_ngn is None:
            return None
        return int(round(self.gen_litres_per_hour * self.petrol_price_ngn))


def load(path="config.toml"):
    p = Path(path)
    if not p.exists():
        cfg = Config()
    else:
        with p.open("rb") as f:
            data = tomllib.load(f)
        known = {f.name for f in fields(Config)}
        unknown = set(data) - known
        if unknown:
            raise ConfigError(f"unknown config keys: {sorted(unknown)}")
        # A key absent from the file means "not set" for the optional fuel values.
        for k in ("gen_litres_per_hour", "petrol_price_ngn"):
            data.setdefault(k, None)
        cfg = replace(Config(), **data)
    validate(cfg)
    return cfg


def validate(cfg):
    if not isinstance(cfg.lat, (int, float)) or not -90 <= cfg.lat <= 90:
        raise ConfigError(f"lat must be between -90 and 90, got {cfg.lat!r}")
    if not isinstance(cfg.lon, (int, float)) or not -180 <= cfg.lon <= 180:
        raise ConfigError(f"lon must be between -180 and 180, got {cfg.lon!r}")
    if cfg.debounce_s < 1 or cfg.poll_s < 1:
        raise ConfigError("debounce_s and poll_s must be at least 1")
