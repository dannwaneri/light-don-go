"""Pick one activity by rule. No numbers in any activity, so the guard stays simple."""

DAY_DRY = [
    "walk to the junction and buy roasted plantain and fish",
    "take a slow walk round the street",
    "go greet the neighbours by the gate",
    "walk to the kiosk for cold mineral and come back",
    "sit under the tree outside and watch the road",
]
RAINING = [
    "sit on the veranda and watch the rain, phone inside",
    "stand by the window and stretch your back and legs",
    "gist with whoever is in the house, screens down",
]
AFTER_DARK = [
    "sit outside in the compound and catch the evening breeze",
    "walk to the junction for suya and come straight back",
    "gist with the neighbours by the gate",
    "sit outside and look at the stars while the street is dark",
]


def pick(facts, outage_id):
    if facts.is_raining:
        category, pool = "raining", RAINING
    elif facts.after_sunset:
        category, pool = "after_dark", AFTER_DARK
    else:
        category, pool = "day_dry", DAY_DRY
    facts.category = category
    facts.activity = pool[outage_id % len(pool)]
    return facts.activity
