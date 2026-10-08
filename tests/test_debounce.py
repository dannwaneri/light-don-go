from light_don_go.power import Debouncer


def feed(d, seq):
    """seq: list of (plugged, t). Returns the non-None events."""
    return [e for p, t in seq if (e := d.update(p, t))]


def test_short_drop_is_flicker():
    d = Debouncer(30, 15)
    assert feed(d, [(True, 0), (False, 5), (False, 10), (True, 15)]) == ["flicker"]


def test_long_drop_is_one_outage_then_power_back():
    d = Debouncer(30, 15)
    ev = feed(d, [(False, 0), (False, 20), (False, 30), (False, 35), (False, 600), (True, 900)])
    assert ev == ["outage_start", "power_back"]


def test_second_outage_inside_cooldown_is_quiet():
    d = Debouncer(30, 15)
    ev = feed(d, [(False, 0), (False, 30), (True, 100),          # outage 1
                  (False, 400), (False, 430), (True, 500)])        # 400 s later: inside 15 min
    assert ev == ["outage_start", "power_back", "outage_quiet", "power_back"]


def test_outage_after_cooldown_nudges_again():
    d = Debouncer(30, 15)
    ev = feed(d, [(False, 0), (False, 30), (True, 100),
                  (False, 1000), (False, 1030)])                   # 1000 s later: after 15 min
    assert ev == ["outage_start", "power_back", "outage_start"]


def test_seconds_on_battery():
    d = Debouncer(30, 15)
    feed(d, [(False, 10), (False, 40)])
    assert d.seconds_on_battery(100) == 90
