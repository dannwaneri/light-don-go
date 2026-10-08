import pytest

from light_don_go.guard import check, check_nudge
from conftest import make_facts

F = make_facts(minutes_left=75, go_until="18:21", battery=41, naira=1500)

PASS = [
    "Abeg close the laptop, walk to the junction before 18:21 and buy plantain.",
    "Light don go, you get 75 minutes before sunset, go buy roasted plantain and fish.",
    "Sun go set by 6:21pm, waka go junction now.",
    "Sun go set by 6:21 pm, waka go junction now.",
    "You get about one hour before dark, go outside.",
    "You get one and a half hours, go outside now.",
    "Battery na 41%, close am and go buy plantain.",
    "Hold the gen one hour, save ₦1,500, go buy plantain.",
    "Every hour the gen rest na 1500 naira for your pocket.",
    "Save N1500, no on gen, go waka small.",
    "Go buy roasted plantain and fish now, abeg close the laptop.",
    "Before 6:30pm sun don set, so move now.",        # within 10 min of 18:21
    "Sun go set by 6.21, go out now.",                 # no am/pm: 12 h either way
]

FAIL = [
    ("You get 3 hours before rain, go outside.", "3 hours"),
    ("You get 120 minutes before dark.", "120 minutes"),
    ("Battery na 50%, go out.", "50%"),
    ("Save ₦2,000 if you hold the gen.", "₦2,000"),
    ("Go out by 5pm.", "5pm"),
    ("Go out by 17:00.", "17:00"),
    ("You get two hours, go.", "two hours"),
    ("Walk 3 streets and come back.", "3"),
    ("Half an hour remain, go now.", "Half an hour"),
    ("Go before 7 o'clock.", "7 o'clock"),
]


@pytest.mark.parametrize("text", PASS)
def test_pass(text):
    r = check(text, F)
    assert r.ok, (text, r)


@pytest.mark.parametrize("text,bad", FAIL)
def test_fail_names_the_bad_number(text, bad):
    r = check(text, F)
    assert not r.ok
    assert bad in r.bad, r


def test_time_tolerance_edge():
    assert check("Go before 18:31.", F).ok           # +10 min
    assert not check("Go before 18:32.", F).ok       # +11 min
    assert not check("Go before 18:10.", F).ok       # -11 min


def test_minutes_tolerance_edge():
    assert check("You get 80 minutes.", F).ok        # +5
    assert not check("You get 81 minutes.", F).ok    # +6


def test_no_numbers_passes():
    assert check("Close the laptop and go greet the neighbours by the gate.", F).ok


def test_over_25_words_fails():
    r = check(" ".join(["go"] * 26), F)
    assert not r.ok and any(x.startswith("too_long") for x in r.reasons)


def test_empty_fails():
    assert not check("   ", F).ok


def test_time_when_no_window_fails():
    night = make_facts(minutes_left=None, go_until=None, after_sunset=True)
    assert not check("Go out before 18:21.", night).ok
    assert not check("You get 75 minutes.", night).ok
    assert check("Go sit outside in the compound, close the laptop.", night).ok


def test_no_fuel_fact_rejects_naira():
    f = make_facts(naira=None, minutes_left=140)
    assert not check("Save ₦1,500 now.", f).ok
    assert not check("Hold the gen one hour.", f).ok      # 60 vs 140 left, and no fuel fact
    assert check("Hold the gen one hour.", make_facts(minutes_left=140)).ok   # fuel fact allows it


@pytest.mark.parametrize("text", [
    "E be like NEPA light don come Port Harcourt, go sit outside.",
    "Close your laptop now, before the generator dies.",
    "Close the laptop before any person on the gen.",
    "Abeg go out for 10 minutes.",
    "Go before 6pm.",
    " ".join(["go"] * 21),
])
def test_nudge_guard_rejects(text):
    assert not check_nudge(text).ok


@pytest.mark.parametrize("text", [
    "Abeg shut that laptop, go sit for veranda and enjoy small breeze.",
    "Oya close am, waka go junction buy roasted plantain and fish.",
    "Gentle waka round the street go do you good, close that screen.",   # 'gentle' is not 'gen'
])
def test_nudge_guard_accepts(text):
    assert check_nudge(text).ok, check_nudge(text)
