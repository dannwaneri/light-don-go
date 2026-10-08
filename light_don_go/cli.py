"""ldg watch | simulate | refresh"""
import argparse
import sys
import time
from datetime import datetime, timezone

from . import config, display, forecast, log, power, run, writer

CACHE = "cache/forecast.json"
LOG = "logs/outages.jsonl"


def cmd_refresh(cfg, args):
    ok = forecast.refresh(cfg, CACHE)
    print("forecast saved" if ok else "forecast refresh failed (old cache kept)")
    return 0 if ok else 1


def cmd_simulate(cfg, args):
    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(cfg.tz).date()
    hh, mm = map(int, args.at.split(":"))
    now_utc = datetime(day.year, day.month, day.day, hh, mm, tzinfo=cfg.tz).astimezone(timezone.utc)
    fc = forecast.load(args.forecast or CACHE, now_utc)
    f = run.build_facts(cfg, args.battery, now_utc=now_utc, fc=fc)
    outage_id = int(now_utc.timestamp() // 60)
    if args.no_model:
        def write(*_a, **_k):
            raise writer.ModelUnavailable("--no-model")
    else:
        write = writer.write
    rec = run.handle_outage(f, cfg, outage_id, write=write)
    rec.update(kind="simulated", start=now_utc)
    log.append(rec, LOG)
    display.show(rec["message"], use_toast=not args.no_toast)
    print(f"source={rec['source']} guard={rec['guard']} attempts={len(rec['attempts'])} "
          f"forecast={'ok' if f.forecast_ok else 'none'}")
    for a in rec["attempts"]:
        print(f"  [{'ok' if a['guard_ok'] else 'REJECT'}] {a['text']}  {a['bad_numbers'] or ''}")
    return 0


def cmd_watch(cfg, args):
    try:
        p = power.read()
    except power.NoBattery as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"watching power (plugged={p['plugged']}, battery={p['pct']}%). Ctrl+C to stop.")
    print("warming model..." , "ok" if writer.warm_up(cfg) else "model not reachable (template will be used)")
    deb = power.Debouncer(cfg.debounce_s, cfg.cooldown_min)
    last_refresh = 0.0
    try:
        while True:
            t = time.monotonic()
            p = power.read()
            if p["plugged"] and t - last_refresh >= cfg.refresh_min * 60:
                forecast.refresh(cfg, CACHE)
                last_refresh = t
            ev = deb.update(p["plugged"], t)
            now_utc = datetime.now(timezone.utc)
            if ev == "outage_start":
                f = run.build_facts(cfg, p["pct"], now_utc=now_utc, cache=CACHE)
                rec = run.handle_outage(f, cfg, int(now_utc.timestamp() // 60))
                if power.read()["plugged"]:
                    rec.update(kind="power_back", note="power returned before message; cancelled",
                               start=now_utc, on_battery_s=deb.seconds_on_battery(time.monotonic()))
                    deb.update(True, time.monotonic())
                else:
                    rec.update(kind="outage", start=now_utc)
                    display.show(rec["message"], use_toast=not args.no_toast)
                log.append(rec, LOG)
            elif ev in ("flicker", "outage_quiet", "power_back"):
                log.append({"kind": ev, "at": now_utc, "battery_pct": p["pct"],
                            "on_battery_s": round(deb.seconds_on_battery(t) or 0)}, LOG)
                print(f"{now_utc.astimezone(cfg.tz):%H:%M:%S} {ev}")
            time.sleep(cfg.poll_s)
    except KeyboardInterrupt:
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ldg", description="Light don go: go outside before you on the gen.")
    ap.add_argument("--config", default="config.toml")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("watch", help="watch power and nudge on a real outage")
    w.add_argument("--no-toast", action="store_true")
    s = sub.add_parser("simulate", help="run the full flow for a given time and battery")
    s.add_argument("--at", required=True, help="local time HH:MM")
    s.add_argument("--battery", type=int, required=True)
    s.add_argument("--date", help="YYYY-MM-DD (default today)")
    s.add_argument("--forecast", help="forecast cache file (default cache/forecast.json)")
    s.add_argument("--no-model", action="store_true")
    s.add_argument("--no-toast", action="store_true")
    sub.add_parser("refresh", help="save the forecast now")
    args = ap.parse_args(argv)
    try:
        cfg = config.load(args.config)
    except config.ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    return {"watch": cmd_watch, "simulate": cmd_simulate, "refresh": cmd_refresh}[args.cmd](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
