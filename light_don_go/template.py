"""Code-written text. The facts line carries every number; the model never writes one.

Timing test 2026-10-08: when Gemma E2B wrote the whole message it dropped every number and
twice inverted the meaning ("NEPA light don come", "before the generator dies"). So code says
what happened and what the numbers are; the model only writes the nudge.
"""


def time_left(minutes):
    """Minutes under 90 stay exact; longer windows round to the nearest half hour."""
    if minutes < 90:
        return f"{minutes} minutes"
    h = round(minutes / 30) / 2
    return f"about {h:g} hours"


def facts_line(f):
    if f.is_raining:
        s = "Light don go, and rain dey fall."
    elif f.after_sunset:
        s = "Light don go, and night don reach."
    elif f.go_reason == "rain":
        s = f"Light don go. Rain fit start around {f.go_until:%H:%M}: you get {time_left(f.minutes_left)}."
    else:
        s = f"Light don go. Sun go set {f.go_until:%H:%M}: you get {time_left(f.minutes_left)}."
    if f.naira_saved_per_hour is not None:
        s += f" Hold the gen: ₦{f.naira_saved_per_hour:,} saved every hour e rest."
    return s


def nudge(f):
    """Fallback nudge when the model is down or fails the guard twice."""
    if f.after_sunset and not f.is_raining:
        return f"Close the laptop and {f.activity}, near house."
    return f"Close the laptop and {f.activity}."
