"""Read laptop power state and turn raw readings into outage events."""
import psutil


class NoBattery(RuntimeError):
    pass


def read():
    b = psutil.sensors_battery()
    if b is None:
        raise NoBattery("no battery found: this tool needs a laptop that runs on battery when the light goes")
    return {"plugged": bool(b.power_plugged), "pct": int(round(b.percent))}


class Debouncer:
    """Pure state machine. Feed it (plugged, t) every poll; t is seconds (monotonic).

    Events: "flicker", "outage_start", "outage_quiet" (outage inside cooldown), "power_back".
    """

    def __init__(self, debounce_s=30, cooldown_min=15):
        self.debounce_s = debounce_s
        self.cooldown_s = cooldown_min * 60
        self.state = "on"
        self.since = None          # when the laptop went on battery
        self.last_nudge = None     # battery-start time of the last real outage_start

    def update(self, plugged, t):
        if self.state == "on":
            if not plugged:
                self.state, self.since = "pending", t
            return None
        if self.state == "pending":
            if plugged:
                self.state = "on"
                return "flicker"
            if t - self.since >= self.debounce_s:
                self.state = "out"
                if self.last_nudge is not None and self.since - self.last_nudge < self.cooldown_s:
                    return "outage_quiet"
                self.last_nudge = self.since
                return "outage_start"
            return None
        # state == "out"
        if plugged:
            self.state = "on"
            return "power_back"
        return None

    def seconds_on_battery(self, t):
        return None if self.since is None else t - self.since
