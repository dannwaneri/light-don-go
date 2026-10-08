# Light don go — Spec

Hacktoberfest Open-Source AI Challenge, Week 1: Touch Grass.
Deadline: Sun 2026-10-11, 11:59 PM PDT (Mon 2026-10-12, 07:59 WAT).

---

## SECTION 1: SPEC

**One-line purpose**
When NEPA takes light, and before anyone starts the generator, the laptop gives you one short plan to go outside, then tells you to close it.

**Home setup (confirmed by Daniel, 2026-10-07)**
- No inverter. There is a generator, started by hand.
- When NEPA goes, the laptop goes to battery and the router goes off. The internet stays off until the generator starts.
- When the generator starts, the laptop gets mains power again. The laptop cannot tell generator power from NEPA power.
- So the tool acts in the gap between NEPA going and the generator starting. The message is "go out before you on the gen".

**Users and use cases**
- As a Port Harcourt remote worker, I want a quick nudge when NEPA takes light so that I go outside instead of draining my battery on my phone.
- As the same user, I want the plan to respect the weather and the time of day so that I don't walk into rain or darkness.
- As the same user, I want the tool to work with no internet so that it still works when the router dies with the power.
- As the author (Daniel), I want a log of real outages and what the tool said so that I can report a real field test in the post.

**Requirements**
1. The tool detects a power cut within 60 seconds of the laptop switching from mains to battery.
2. The tool ignores a drop shorter than 30 s (a NEPA flicker, or a generator that someone starts at once). [ASSUMPTION: 30 s]
2a. When mains power returns, the tool logs `power_back` with the time on battery. It does not claim that NEPA came back, because the laptop cannot tell NEPA from the generator.
2b. Optional: if `gen_litres_per_hour` and `petrol_price_ngn` are set in the config, the facts include the naira saved per hour the generator stays off, and the message may use this number. [ASSUMPTION: Daniel wants the fuel angle; the values come from his own config, not from the internet]
3. While power is on and internet works, the tool saves the hourly forecast for the next 24 h for one fixed place.
4. After a cut, the tool uses only saved data and local computing. It makes no network calls.
5. A rule-based step computes the facts: time now, minutes of dry weather left, minutes of daylight left, temperature now, battery percent. It also picks one activity from a fixed list.
6. A local open-weight model writes one sentence (25 words or fewer) in Nigerian English that suggests the plan. [ASSUMPTION: light Pidgin flavour, readable to non-Nigerians]
7. Every number in the sentence must match a fact. If not, the tool asks once more. If the second sentence also fails, the tool uses a fixed template. There is a maximum of 2 model calls per outage.
8. The tool shows the message, then a "close the laptop" line, and does not show anything else for the rest of that outage.
9. The tool logs each outage: start, end, facts, model sentence(s), guard result, final message.
10. A simulate mode runs the full flow on demand, for the demo video.

**Edge cases**
- **Saved forecast is old (more than 6 h) or missing:** the tool does not mention rain or temperature. It uses only daylight and battery facts.
- **It is raining now:** the plan is an indoor-but-off-screen one (stretch, sit by the window, gist with neighbours on the veranda). It still says close the laptop.
- **After sunset:** the plan stays near home (compound, gate, veranda, buy suya at the junction). It does not suggest a long walk.
- **Battery 15% or less:** the message adds that the laptop must sleep now.
- **Model is not running or times out (more than 20 s):** the tool uses the template with no retry.
- **Power returns before the message shows (for example, the generator starts within a minute):** the tool cancels the message and logs `power_back` with the time on battery.
- **The generator is switched off later (to refuel, or at night):** this looks like a new outage. If it is outside the 15 min cooldown, the tool nudges again. This is correct behaviour.
- **Laptop has no battery or the battery cannot be read:** the tool exits at start with a clear error.
- **Second cut inside 15 minutes of the last one:** the tool does not nudge again. [ASSUMPTION: no repeat nudge inside 15 min]
- **Model writes a time as "6pm" or "18:00", or minutes as "two hours":** the guard normalises these before comparing.

**Acceptance criteria**
```
Given power is on and a forecast was saved 1 h ago
When the laptop runs on battery for 30 s
Then one message and the close-the-laptop line are shown within 60 s of the cut

Given the laptop switches to battery for 10 s and then back to mains
When the tool checks power
Then no message is shown and the event is logged as a flicker

Given the network is down after the cut
When the tool builds the message
Then no network call is made (verified by a test that fails on any socket use)

Given the facts say rain starts in 120 min
When the model writes "you get 3 hours before rain"
Then the guard rejects it and the tool asks the model one more time

Given both model sentences fail the guard
When the tool builds the message
Then the template message is shown and the log records guard=fallback

Given the model is not running
When an outage starts
Then the template message is shown within 25 s and the log records model=unavailable

Given the saved forecast is 8 h old
When an outage starts
Then the message has no rain or temperature numbers

Given the time is after sunset
When an outage starts
Then the activity picked is from the near-home list

Given battery is 12%
When an outage starts
Then the message tells the user to sleep the laptop now

Given simulate mode is started with --at 16:30 --battery 41
When it runs
Then it prints the same message the real flow would build for those inputs, and logs it marked simulated
```

---

## SECTION 2: PLAN

**Stack and architecture**
- Python 3.12+ single package, runs as a console app on Windows 11. [ASSUMPTION: Python, matching the user's other tools]
- Power: `psutil.sensors_battery()` polled every 5 s.
- Weather: Open-Meteo hourly forecast (free, no key), saved to a JSON file every 30 min while power and internet are on. [ASSUMPTION: Open-Meteo]
- Sunset: computed locally from latitude and longitude, so it needs no network.
- Model: Gemma via Ollama on `localhost:11434`. [ASSUMPTION: a small Gemma 4 model that runs on the laptop CPU in under 20 s — pick the exact tag after a timing test]
- Display: console output plus one Windows toast notification. [ASSUMPTION: a toast is enough; no GUI window]
- Flow: `watcher → debounce → facts (rules) → picker (rules) → writer (model) → guard → message → log`.

The model never decides anything. Rules pick the activity and compute every number. The model only phrases the sentence.

**Data model**
- `config.toml`: `lat`, `lon`, `place_name`, `tz` (default Port Harcourt 4.8156, 7.0498, Africa/Lagos tz), `debounce_s=30`, `cooldown_min=15`, `model`, `model_timeout_s=20`, `gen_litres_per_hour=1.0` (Daniel, 2026-10-07), `petrol_price_ngn=1500` (Daniel, 2026-10-07). So `naira_saved_per_hour` = 1500. If either value is removed from the config, the message has no fuel line.
- Log `kind` values: `outage | flicker | power_back | simulated`.
- `Facts` also has `naira_saved_per_hour|None`. The guard allows this number exactly, with or without the "₦" sign and commas.
- `cache/forecast.json`: `{fetched_at, hours: [{time, precip_prob, precip_mm, temp_c}]}`.
- `logs/outages.jsonl`: one row per event: `{id, start, end, kind: outage|flicker|simulated, facts, attempts: [{text, guard_ok, bad_numbers}], final, source: model|template, model_status}`.
- `Facts`: `now, dry_min|None, daylight_min, temp_c|None, battery_pct, forecast_age_min|None, is_raining, after_sunset, activity`.

**Model (measured 2026-10-08):** `gemma4:e2b-it-qat`, warm 3.6–4.0 s per call. The 20 s timeout stays as a safety margin. The first call after boot is about 14 s, so `ldg watch` sends one warm-up call at start.

**Split design (Daniel approved 2026-10-08, after the first real runs):** code writes the facts line (what happened, the time limit, minutes left, ₦ saved); Gemma writes only the nudge sentence. The model sees no numbers (`place`, `situation`, `activity` only), and `guard.check_nudge` rejects any number, more than 20 words, or any mention of NEPA/light/power/generator/gen. Reason: in 4 whole-message runs Gemma dropped every number and twice inverted the meaning ("NEPA light don come", "before the generator dies"). After the split: 9 of 9 runs passed on the first try, with no meaning errors seen.

**Wet hour (changed 2026-10-08):** precip_prob ≥ 70% or precip_mm ≥ 0.5. The 50% rule kept Port Harcourt indoors almost all day in rainy season.

**Facts shown to the model (SUPERSEDED by the split design above):** only `go_until` (the earlier of rain start and sunset), `minutes_left` (until go_until), `battery_pct`, `naira_saved_per_hour` and `activity`. Do not show the time now or the later of the two limits; the model used them wrongly in the timing test.

**Function contracts**
- `power.read() -> {plugged: bool, pct: int}`. Raises `NoBattery`.
- `Debouncer.update(plugged, t) -> None | "outage_start" | "outage_end" | "flicker"`.
- `forecast.refresh(cfg) -> bool`. Never raises; returns False on any network error.
- `forecast.load(path, now) -> Forecast | None`. Returns None if the file is missing or older than 6 h.
- `facts.build(now, forecast, battery_pct, cfg) -> Facts`.
- `picker.pick(facts) -> Activity` (fixed lists: day-dry, day-rain, after-sunset).
- `writer.write(facts, retry_hint=None) -> str | ModelUnavailable` (one HTTP call to Ollama, temperature 0.7, max 60 tokens).
- `guard.check(text, facts) -> {ok, bad_numbers}`. Extracts every number, time and number word, normalises them, and checks each against the allowed set (dry_min ± 5, the same in hours rounded, daylight_min ± 5, temp ± 1, battery exact, the clock time of rain start and sunset ± 10 min). It also fails if the text is more than 25 words.
- `template.render(facts) -> str`.
- `run.handle_outage(facts) -> final_message` (at most 2 writer calls, then the template).

**Patterns to follow**
- Bounded: a maximum of 2 model calls per outage, with no loops on model output (from the user's standing rule).
- Code decides, model phrases (the same pattern as the VES benchmark and golden-hour).
- [ASSUMPTION: new repo `C:\Users\DELL\light-don-go`, no shared code with other projects]

**Testing strategy**
- Unit: debouncer (flicker, outage, cooldown), facts (stale forecast, raining now, after sunset), picker, guard (heavy: correct numbers, wrong numbers, "6pm"/"18:00", "two hours", extra words), template.
- Integration: `handle_outage` with a fake writer that returns bad-then-bad, bad-then-good, and unavailable. Assert the call count is 2 or fewer.
- Offline test: patch `socket.socket` to raise, then run `handle_outage` with the template path and a fake writer. Only the Ollama call to localhost is allowed.
- Mutation check on the guard: change one tolerance in the code and confirm that a test fails.
- Manual: a real unplug test on the laptop, and the first real NEPA outage (for the post).

**Security and performance**
- No data leaves the laptop after the cut. Before the cut, only lat/lon goes to the weather API.
- From cut to message: 60 s or less with the model, 35 s or less on the template path.
- The watcher uses less than 1% CPU while idle.

---

## SECTION 3: TASKS

## Task 1: Project skeleton and config
**What to build:** A Python package `light_don_go` with `config.toml` loading and defaults for Port Harcourt, plus a `pyproject.toml` with the `psutil`, `httpx` and `tomli`-compatible standard library. The CLI entry `ldg` has the subcommands `watch`, `simulate`, `refresh`.
**Files:** `pyproject.toml`, `light_don_go/__init__.py`, `light_don_go/config.py`, `light_don_go/cli.py`, `config.toml`, `README.md`
**Acceptance criteria:** 1) `ldg --help` lists the 3 subcommands. 2) A missing config file uses the Port Harcourt defaults. 3) Bad lat/lon values give a clear error.
**Dependencies:** none

## Task 2: Power reader and debouncer
**What to build:** `power.read()` wraps psutil. `Debouncer` is a pure state machine with `debounce_s` and `cooldown_min`.
**Files:** `light_don_go/power.py`, `tests/test_debounce.py`
**Acceptance criteria:** 1) 10 s on battery then plugged in → `flicker`. 2) 30 s on battery → `outage_start` once, and plugged in → `outage_end`. 3) A second outage inside 15 min gives no `outage_start`.
**Dependencies:** Task 1

## Task 3: Forecast fetch and cache
**What to build:** `refresh` calls Open-Meteo hourly (precipitation_probability, precipitation, temperature_2m) for 24 h and writes `cache/forecast.json` atomically. `load` returns None if the file is missing or more than 6 h old.
**Files:** `light_don_go/forecast.py`, `tests/test_forecast.py` (with a recorded fixture response)
**Acceptance criteria:** 1) Writes a valid cache from the fixture. 2) A network error returns False and keeps the old cache. 3) `load` on a 7 h old file returns None.
**Dependencies:** Task 1

## Task 4: Facts and activity picker
**What to build:** `facts.build` computes sunset locally (NOAA formula, no network), `dry_min` (minutes until the first hour with precip_prob ≥ 50% or precip_mm ≥ 0.5), `is_raining`, `after_sunset` and battery. `picker.pick` chooses from 3 fixed lists of Port Harcourt-flavoured activities (for example: buy roasted plantain and fish at the junction, walk to the junction, sit outside with neighbours) in rotation, picked by outage id.
**Files:** `light_don_go/facts.py`, `light_don_go/picker.py`, `tests/test_facts.py`
**Acceptance criteria:** 1) Port Harcourt sunset on 2026-10-07 is within 3 min of the published time. 2) A stale forecast gives `dry_min=None, temp_c=None`. 3) After sunset, the activity is always from the near-home list.
**Dependencies:** Task 3

## Task 5: Numeric guard
**What to build:** `guard.check(text, facts)` with normalisation for digits, "6pm", "6:30pm", "18:00", "two hours", "half an hour", "%" and "°C". Tolerances as in the plan. Fails if the text is more than 25 words.
**Files:** `light_don_go/guard.py`, `tests/test_guard.py` (at least 20 cases)
**Acceptance criteria:** 1) All number formats listed are parsed. 2) A text with any number not in the allowed set fails and lists that number in `bad_numbers`. 3) A text with no numbers passes.
**Dependencies:** Task 4

## Task 6: Model writer and template
**What to build:** `writer.write` makes one POST to Ollama `/api/generate` with a fixed prompt (facts as JSON, a rule to use only those numbers, Nigerian English, 25 words or fewer). On retry it adds the list of bad numbers. A timeout or connection error returns `ModelUnavailable`. `template.render` covers all fact combinations.
**Files:** `light_don_go/writer.py`, `light_don_go/template.py`, `light_don_go/prompt.txt`, `tests/test_template.py`
**Acceptance criteria:** 1) With Ollama off, it returns `ModelUnavailable` in 20 s or less. 2) The template never shows a None value. 3) A timing test on the laptop is recorded in the README (model tag and seconds per call).
**Dependencies:** Task 4

## Task 7: Outage handler, display, log
**What to build:** `handle_outage` is facts → pick → write → guard → (one retry) → template fallback → show the console message and toast → append to the log. `ldg watch` is the main loop (refresh the forecast every 30 min while plugged in; handle events). `ldg simulate --at HH:MM --battery N [--forecast file] [--no-model]`.
**Files:** `light_don_go/run.py`, `light_don_go/display.py`, `light_don_go/log.py`, `tests/test_run.py`
**Acceptance criteria:** 1) The fake writer bad/bad gives the template, logs 2 attempts, and makes 2 calls at most. 2) The offline socket test passes. 3) `ldg simulate` prints a message and writes a `simulated` log row.
**Dependencies:** Tasks 2, 5, 6

## Task 8: Field test and post material [HUMAN]
**What to build:** Daniel runs `ldg watch` through at least one real outage and acts on the message. Then the outage log rows go into the post, with an "it got X wrong" section if there is one. Record the demo with `ldg simulate`.
**Files:** `logs/outages.jsonl`, `POST.md` (Daniel writes it in his own voice)
**Acceptance criteria:** 1) At least one `kind: outage` row from a real cut. 2) The post uses the DEV template sections and enters the Best Use of Gemma category. 3) The repo is public and linked.
**Dependencies:** Task 7

**Review checkpoint:** Before you start the build, run one Ollama timing test on this laptop. If the chosen Gemma model takes more than 20 s per call, pick a smaller tag first, because every timeout and latency number above depends on it.

---

## Assumptions to review

1. ~~Model speed~~ — RESOLVED 2026-10-08: `gemma4:e2b-it-qat` (4.3 GB, Ollama 0.35.0, i5-1135G7 CPU) cold 14.1 s (7.9 s load), warm 3.6–4.0 s, ~15–20 t/s, 26–34 tokens. Script: `bench/time_model.py`.
1a. Window = min(dry_min, daylight_min), and only that end time is shown to the model — Impact: HIGH (from the timing test: with rain at 18:30 and sunset at 17:45, the model said "before 18:30", which passes the number check but sends you out into the dark).
   Correct this if: you want the model to see all facts.
2. ~~Power cut = laptop switches to battery~~ — RESOLVED 2026-10-07: no inverter, generator started by hand, so the laptop does see the cut.
3. A drop shorter than 30 s is a flicker, not an outage — Impact: MEDIUM
   Correct this if: NEPA often flickers for longer than 30 s before it really goes.
3a. Fuel-saved number in the message: 1 L/h × ₦1,500/L = ₦1,500 per hour (set 2026-10-07) — Impact: MEDIUM
   Correct this if: you don't want money in the message. It is optional in the config.
4. Python console app plus Windows toast, no GUI — Impact: MEDIUM
   Correct this if: you want a tray icon or a phone version for the demo.
5. Open-Meteo for the forecast, one fixed location (Lagos default) — Impact: MEDIUM
   Correct this if: you are not in Lagos; set your real lat/lon.
6. Nigerian English with light Pidgin flavour — Impact: MEDIUM
   Correct this if: you want full Pidgin or plain English.
7. Forecast older than 6 h is treated as unknown — Impact: LOW
   Correct this if: outages often last long enough that the cache is always stale; maybe 12 h.
8. No repeat nudge inside 15 min — Impact: LOW
   Correct this if: NEPA flips on and off often and you want a nudge each time.
9. New standalone repo at `C:\Users\DELL\light-don-go` — Impact: LOW
