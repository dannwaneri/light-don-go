"""Outage handler: facts -> pick -> write -> guard -> (one retry) -> template fallback."""
from datetime import datetime, timezone

from . import facts as facts_mod
from . import forecast, guard, picker, template, writer

MAX_MODEL_CALLS = 2
LOW_BATTERY = 15
CLOSE_LINE = "Close the laptop. Go outside."
CLOSE_LINE_RAIN = "Close the laptop. Rest your eyes."


def close_line(f):
    return CLOSE_LINE_RAIN if f.is_raining else CLOSE_LINE


def compose(nudge, f):
    lines = [template.facts_line(f), nudge]
    if f.battery_pct <= LOW_BATTERY:
        lines.append(f"Battery {f.battery_pct}%: sleep the laptop now.")
    lines.append(close_line(f))
    return "\n".join(lines)


def handle_outage(f, cfg, outage_id, write=writer.write):
    """Return a log record. At most MAX_MODEL_CALLS calls to `write`; no loops on model output."""
    picker.pick(f, outage_id)
    view = f.model_view(cfg.place_name)
    attempts, final, source, model_status = [], None, "template", "ok"
    retry = ""
    for _ in range(MAX_MODEL_CALLS):
        try:
            text = write(view, cfg, retry)
        except writer.ModelUnavailable as e:
            model_status = f"unavailable: {e}"
            break
        g = guard.check_nudge(text)
        attempts.append({"text": text, "guard_ok": g.ok, "bad_numbers": g.bad, "reasons": g.reasons})
        if g.ok:
            final, source = text, "model"
            break
        retry = writer.retry_hint(g)
    if final is None:
        final = template.nudge(f)
    message = compose(final, f)
    return {
        "outage_id": outage_id,
        "facts": f,
        "model_view": view,
        "attempts": attempts,
        "source": source,
        "guard": "pass" if source == "model" else ("fallback" if attempts else "skipped"),
        "model_status": model_status,
        "final": final,
        "message": message,
    }


def build_facts(cfg, battery_pct, now_utc=None, cache="cache/forecast.json", fc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    if fc is None:
        fc = forecast.load(cache, now_utc)
    return facts_mod.build(now_utc, fc, battery_pct, cfg)
