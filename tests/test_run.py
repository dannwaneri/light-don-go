import json
import socket

import pytest

from light_don_go import facts as facts_mod, log, run, template, writer
from light_don_go.guard import check, check_nudge
from conftest import make_facts


class FakeWriter:
    def __init__(self, replies):
        self.replies, self.calls, self.retries = list(replies), 0, []

    def __call__(self, view, cfg, retry=""):
        self.calls += 1
        self.retries.append(retry)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


BAD = "You get 3 hours before rain, go."
GOOD = "Abeg close the laptop, waka go junction buy roasted plantain and fish."


def test_bad_bad_gives_template_and_two_calls(cfg):
    w = FakeWriter([BAD, BAD, GOOD])
    rec = run.handle_outage(make_facts(), cfg, 1, write=w)
    assert w.calls == 2
    assert rec["source"] == "template" and rec["guard"] == "fallback" and len(rec["attempts"]) == 2
    assert "3 hours" in w.retries[1]


def test_bad_good_uses_model(cfg):
    w = FakeWriter([BAD, GOOD])
    rec = run.handle_outage(make_facts(), cfg, 1, write=w)
    assert w.calls == 2 and rec["source"] == "model" and rec["final"] == GOOD


def test_unavailable_goes_straight_to_template(cfg):
    w = FakeWriter([writer.ModelUnavailable("down"), GOOD])
    rec = run.handle_outage(make_facts(), cfg, 1, write=w)
    assert w.calls == 1 and rec["source"] == "template" and rec["model_status"].startswith("unavailable")


def test_message_is_facts_line_then_nudge(cfg):
    rec = run.handle_outage(make_facts(), cfg, 1, write=FakeWriter([GOOD]))
    lines = rec["message"].splitlines()
    assert lines[0] == template.facts_line(make_facts()) and lines[1] == GOOD


def test_off_topic_nudge_is_rejected_and_retried(cfg):
    w = FakeWriter(["E be like NEPA light don come, go outside.", GOOD])
    rec = run.handle_outage(make_facts(), cfg, 1, write=w)
    assert rec["source"] == "model" and rec["attempts"][0]["reasons"] == ["off_topic"]
    assert "light or the generator" in w.retries[1]


def test_low_battery_line_added(cfg):
    rec = run.handle_outage(make_facts(battery=12), cfg, 1, write=FakeWriter([GOOD]))
    assert "Battery 12%: sleep the laptop now." in rec["message"]
    assert rec["message"].endswith(run.CLOSE_LINE)


def test_close_line_does_not_say_go_outside_in_rain(cfg):
    rec = run.handle_outage(make_facts(raining=True, go_until=None, minutes_left=None), cfg, 1,
                            write=FakeWriter([GOOD]))
    assert rec["message"].endswith(run.CLOSE_LINE_RAIN) and "Go outside" not in rec["message"]


@pytest.mark.parametrize("mins,text", [(75, "75 minutes"), (89, "89 minutes"), (90, "about 1.5 hours"),
                                       (110, "about 2 hours"), (240, "about 4 hours"), (260, "about 4.5 hours")])
def test_time_left_wording(mins, text):
    assert template.time_left(mins) == text


@pytest.mark.parametrize("mins", [90, 104, 110, 135, 240, 255, 400])
def test_long_window_hours_pass_guard(mins):
    f = make_facts(minutes_left=mins)
    t = template.facts_line(f)
    assert check(t, f).ok, t


def test_no_network_after_cut(cfg, monkeypatch, tmp_path):
    """Build facts from cache and handle the outage with every socket blocked."""
    def blocked(*a, **k):
        raise AssertionError("network used after the cut")
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    f = run.build_facts(cfg, 41, cache=tmp_path / "none.json")
    rec = run.handle_outage(f, cfg, 7, write=FakeWriter([writer.ModelUnavailable("x")]))
    log.append(rec, tmp_path / "log.jsonl")
    assert rec["source"] == "template"


@pytest.mark.parametrize("kw", [
    dict(),
    dict(reason="rain", go_until="18:00", minutes_left=54),
    dict(raining=True, go_until=None, minutes_left=None),
    dict(after_sunset=True, go_until=None, minutes_left=None),
    dict(naira=None),
])
def test_facts_line_numbers_always_pass_guard(kw):
    f = make_facts(**kw)
    t = template.facts_line(f)
    assert "None" not in t
    r = check(t, f)
    assert not r.bad, (t, r)


@pytest.mark.parametrize("kw", [dict(), dict(raining=True), dict(after_sunset=True, go_until=None, minutes_left=None)])
def test_fallback_nudge_passes_nudge_guard(kw):
    assert check_nudge(template.nudge(make_facts(**kw))).ok


def test_model_view_has_no_numbers():
    f = make_facts()
    v = f.model_view("Port Harcourt")
    assert not any(ch.isdigit() for ch in str(v))


def test_log_row_is_json(cfg, tmp_path):
    rec = run.handle_outage(make_facts(), cfg, 1, write=FakeWriter([GOOD]))
    rec["kind"] = "simulated"
    log.append(rec, tmp_path / "l.jsonl")
    row = json.loads((tmp_path / "l.jsonl").read_text(encoding="utf-8"))
    assert row["kind"] == "simulated" and row["facts"]["battery_pct"] == 41


def test_takeover_page_has_data_and_cannot_be_broken_by_model_text(cfg, tmp_path):
    from light_don_go import display
    evil = "Abeg close am </script><script>alert(1)</script>"
    rec = run.handle_outage(make_facts(battery=12), cfg, 1, write=FakeWriter([evil, evil]))
    rec["final"] = evil
    display.takeover(rec, out=tmp_path / "t.html", launch=False)
    html = (tmp_path / "t.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)" not in html
    assert r"<\/script>" in html and '"low_battery": true' in html
    assert "/*__DATA__*/" not in html and "const DATA = {" in html
    assert '"situation": "dry daylight"' in html
