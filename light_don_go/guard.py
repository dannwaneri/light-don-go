"""Reject a model sentence if any number in it does not match the facts the model was shown.

Allowed (SPEC 1a, model-visible facts only):
  clock time  -> go_until, within 10 min (12 h times accepted either way if no am/pm)
  duration    -> minutes_left within 5 min; in hours within 30 min; exactly 1 hour if the fuel fact is set
  percent     -> battery_pct exactly
  naira       -> naira_saved_per_hour exactly
  bare number -> equal to minutes_left, battery_pct or naira_saved_per_hour
Also fails on an empty sentence or one over 25 words.

check_nudge() is what the model output goes through: no number of any kind, 20 words max,
and no mention of light or the generator (the code-written facts line covers those).
"""
import re
from dataclasses import dataclass, field

MAX_WORDS = 25
TIME_TOL = 10
MIN_TOL = 5
HOUR_TOL = 30

WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
    "fifty": 50, "sixty": 60, "ninety": 90,
}
NUMWORD = "|".join(sorted(WORDS, key=len, reverse=True))
NUM = r"\d[\d,]*(?:\.\d+)?"

RE_NAIRA = re.compile(rf"(?:₦|\bN|\bNGN\s?)\s?({NUM})|({NUM})\s*(?:naira|NGN)\b", re.I)
RE_PCT = re.compile(rf"({NUM})\s*(?:%|percent\b|per\s?cent\b)", re.I)
RE_TIME = re.compile(
    r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)(?![a-z])"   # 6pm, 6:30 pm
    r"|\b(\d{1,2})[:.](\d{2})\b"                                         # 18:30, 6.30
    r"|\b(\d{1,2})\s*o'?clock\b", re.I)
RE_HALF_HOUR = re.compile(r"\bhalf\s+(?:an?\s+)?hour\b", re.I)
RE_DUR = re.compile(
    rf"\b({NUM}|{NUMWORD})(\s+and\s+a\s+half)?\s*-?\s*(hours?|hrs?|h\b|minutes?|mins?)\b", re.I)
RE_BARE = re.compile(NUM)


@dataclass
class GuardResult:
    ok: bool
    bad: list = field(default_factory=list)      # the offending number text
    reasons: list = field(default_factory=list)
    off_topic: str = ""


def _num(s):
    s = s.replace(",", "")
    return float(s)


def _value(tok):
    t = tok.lower()
    return float(WORDS[t]) if t in WORDS else _num(t)


_NO_FACTS = type("NoFacts", (), dict(battery_pct=None, naira_saved_per_hour=None,
                                     minutes_left=None, go_until=None))()
NUDGE_MAX_WORDS = 20
RE_OFF_TOPIC = re.compile(r"\b(nepa|light|power|electricity|generator|gen)\b", re.I)


def check_nudge(text):
    res = check(text, _NO_FACTS, max_words=NUDGE_MAX_WORDS)
    for m in RE_OFF_TOPIC.finditer(text):
        res.ok = False
        res.reasons.append("off_topic")
        res.off_topic = m.group(0)
        break
    return res


def check(text, facts, max_words=MAX_WORDS):
    res = GuardResult(ok=True)
    words = text.split()
    if not words:
        return GuardResult(False, [], ["empty"])
    if len(words) > max_words:
        res.ok = False
        res.reasons.append(f"too_long:{len(words)}")

    battery = facts.battery_pct
    naira = facts.naira_saved_per_hour
    mins = facts.minutes_left
    go = None if facts.go_until is None else facts.go_until.hour * 60 + facts.go_until.minute
    masked = text

    def bad(span_text, why):
        res.ok = False
        res.bad.append(span_text.strip())
        res.reasons.append(why)

    def consume(m):
        nonlocal masked
        a, b = m.span()
        masked = masked[:a] + " " * (b - a) + masked[b:]

    for m in list(RE_NAIRA.finditer(masked)):
        v = _num(m.group(1) or m.group(2))
        if naira is None or v != naira:
            bad(m.group(0), "naira")
        consume(m)

    for m in list(RE_PCT.finditer(masked)):
        if _num(m.group(1)) != battery:
            bad(m.group(0), "percent")
        consume(m)

    for m in list(RE_TIME.finditer(masked)):
        if m.group(1):
            h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
            if h > 12:
                cands = []
            else:
                h12 = h % 12
                cands = [(h12 + 12) * 60 + mi] if ap.startswith("p") else [h12 * 60 + mi]
        elif m.group(4):
            h, mi = int(m.group(4)), int(m.group(5))
            cands = [h * 60 + mi] if h > 12 else [h * 60 + mi, (h + 12) * 60 + mi]
        else:
            h = int(m.group(6))
            cands = [h * 60, (h + 12) * 60] if h <= 12 else []
        if go is None or not any(abs(c - go) <= TIME_TOL for c in cands):
            bad(m.group(0), "time")
        consume(m)

    for m in list(RE_HALF_HOUR.finditer(masked)):
        if mins is None or abs(30 - mins) > HOUR_TOL:
            bad(m.group(0), "duration")
        consume(m)

    for m in list(RE_DUR.finditer(masked)):
        v = _value(m.group(1)) + (0.5 if m.group(2) else 0)
        unit = m.group(3).lower()
        is_hours = unit.startswith("h")
        dmin = v * 60 if is_hours else v
        ok = mins is not None and abs(dmin - mins) <= (HOUR_TOL if is_hours else MIN_TOL)
        if not ok and is_hours and v == 1 and naira is not None:
            ok = True   # "one hour" of gen off -> naira per hour
        if not ok:
            bad(m.group(0), "duration")
        consume(m)

    allowed = {x for x in (mins, battery, naira) if x is not None}
    for m in RE_BARE.finditer(masked):
        if _num(m.group(0)) not in allowed:
            bad(m.group(0), "number")

    return res
