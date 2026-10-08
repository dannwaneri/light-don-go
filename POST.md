---
title: When NEPA takes light, my laptop tells me to go outside before I on the gen
published: false
tags: devchallenge, hf26challenge, gemma, opensource
cover_image: https://raw.githubusercontent.com/dannwaneri/light-don-go/main/docs/screenshots/takeover-rain.png
---

<!-- DRAFT by Claude from the repo, the logs and this session. Every [DANIEL: ...] needs your own words.
     Rewrite anything that doesn't sound like you. Numbers below are from logs/outages.jsonl and the README.
     Images load from raw.githubusercontent.com, so docs/screenshots/ must be pushed before you publish. -->

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

In Port Harcourt, the light goes and the room changes in about two seconds. The fan stops. The router dies. The laptop drops to battery. Then somebody shouts "on the gen!"

[DANIEL: one or two lines of your own. What you usually do in that gap. Phone on mobile data? Sweating at the desk until the gen comes on?]

That gap, between NEPA taking light and someone starting the generator, is the one moment in my day when the screen is already losing. **Light don go** uses it. When my laptop switches to battery for more than 30 seconds, a full-screen page opens on top of whatever I'm doing:

![Light don go during a real outage: rain, a Gemma nudge to stretch by the window, a 60-second stretch timer, and grass along the bottom](https://raw.githubusercontent.com/dannwaneri/light-don-go/main/docs/screenshots/takeover-rain.png)
*The real outage at 12:31 on 8 October. The big line is Gemma's. The line above it is code.*

It gives me one plan, a 60-second stretch timer (stand up, reach up, roll the shoulders, touch the toes, go outside), and a button: **"I don stand up. Close am."** When the timer ends, it says **"You self don try."** The page doesn't open again until the next cut.

The sky follows the situation. It is warm in the day and counts down to rain or sunset. It is dark at night, with the plan kept near the house:

![Daytime: sunset at 18:20, 50 minutes left, a nudge to walk to the junction for plantain and fish](https://raw.githubusercontent.com/dannwaneri/light-don-go/main/docs/screenshots/takeover-day.png)

![Night: low battery at 12%, a nudge to sit outside and look at the stars, and a warning to sleep the laptop](https://raw.githubusercontent.com/dannwaneri/light-don-go/main/docs/screenshots/takeover-night.png)
*Day and night are simulated runs (`ldg simulate`). The nudges are real Gemma output from those runs, taken from the log.*

The page works with no internet, because the router is already off: it uses no web fonts and loads nothing from a CDN.

It is for anyone who works from a laptop where the power cuts are routine: Nigeria, load-shedding in South Africa, a lot of India and Pakistan. You don't need to explain the problem to any of them.

## Demo

[DANIEL: video or GIF. Suggested 60-90 s cut:
 1. `ldg watch` running, charger in.
 2. Pull the charger. Wait about 35 s (speed up the wait).
 3. The full-screen page takes over. Let the stretch timer run a few seconds, press the button, close the lid.
 4. Cut to the real log rows below.
 For a clean take: `ldg simulate --at 15:10 --battery 63 --forecast tests/fixtures/demo_dry_then_rain.json --takeover`.]

Real outages so far, from `logs/outages.jsonl` (8 October 2026, WAT):

| Time | Event | What the tool did |
|---|---|---|
| 12:23 | NEPA cut | Rain path, indoor activity. Gemma **timed out**; fallback sentence shown |
| 12:25 | Power back after 123 s | Logged (the gen) |
| 12:31 | NEPA cut again | Gemma: *"Abeg shut that laptop, waka go stand by the window stretch back and legs, rain dey down."* Passed the guard first try |
| 12:34 | Power back after 225 s | Logged |

The first real outage found a bug. More on that below.

## Code

{% github dannwaneri/light-don-go %}

## How I Built It

**Detection.** There is no inverter in my house, so when NEPA goes, the laptop really does go to battery. `psutil` reads the power state every 5 seconds. A drop shorter than 30 seconds is a flicker. A second cut within 15 minutes gets logged but not nudged, so NEPA flashing the light on and off doesn't spam you.

**Weather without internet.** When the light goes, the router goes with it. So while power is on, the tool saves the hourly Open-Meteo forecast every 30 minutes. After the cut, it reads only that file. Sunset comes from the NOAA solar formula, computed on the laptop. It gives 18:21 for Port Harcourt on 7 October; Open-Meteo says 18:21 and sunrise-sunset.org says 18:22.

One rule had to change for the rainy season. I first counted an hour as "wet" at a 50% chance of rain. In October in Port Harcourt, almost every hour is over 50%, so the tool kept everyone indoors all day. Now an hour is wet at 70%, or at 0.5 mm of expected rain.

**The model: Gemma 4 E2B, on my CPU.** `gemma4:e2b-it-qat` through Ollama. It is a 4.3 GB download. My laptop is an i5-1135G7 with no NVIDIA GPU. Measured: 14 s cold, 3.6 to 4.0 s warm, about 15 to 20 tokens per second.

**What the model is allowed to do.** This is the part I care about most.

My first version let Gemma write the whole message from the facts. In 4 test runs it dropped every number, and twice it turned the meaning upside down:

> "E be like NEPA light don **come** Port Harcourt…"

That means the light came *back*.

> "Close your laptop now, before the generator **dies**…"

The generator wasn't on.

A check on the numbers could not catch either of these, because neither sentence had a number in it.

So I split the job:

- **Code writes the facts line.** It says what happened, when the rain or sunset comes, the minutes left, and the naira saved. Every number in the message comes from code.
- **Gemma writes only the nudge.** It sees three things: the place, the situation ("raining now", "dry daylight", "after dark") and an activity picked by rule. It sees no numbers at all.
- **A guard checks the nudge.** It rejects the nudge if it has any number, more than 20 words, or any mention of NEPA, light, power or the generator. Gemma gets one retry, with the reason. If the retry fails too, a fixed sentence is used. That is two model calls at most, and never a loop.

After the split, 9 of 9 test runs passed first time, with no meaning errors that I saw.

[DANIEL: link to your VES benchmark post here if it's live. Same pattern: models catch a wrong label when asked, then copy it into a routine note. Small models are fine at tone and unreliable at facts, so don't hand them the facts.]

**What the guard can't do.** It checks numbers and topic, not sense. In one test run Gemma wrote "watch the rain inside the phone", and it passed. A bigger model would make fewer sentences like that, but it would not run on this laptop. I chose the small model, and I accept that one of its sentences will sometimes be odd.

**The bug a real outage found.** At 12:23 the light went, the tool caught it, and Gemma timed out. I measured before changing anything. `ollama ps` showed that the model had just been loaded, by the request that failed. Ollama unloads an idle model after 5 minutes. My warm-up had run at 11:53, so at 12:23 the tool hit a cold start, on battery, and took more than 20 s. The fix is one setting: `keep_alive: -1`, which keeps Gemma in RAM (3.9 GB of my 15.7). At the next cut, at 12:31, Gemma answered first time.

So the defaults broke the one promise the tool makes, which is to work when the light goes. I would not have found that in a simulation.

**The page.** One HTML file with the outage data written in as JSON. Edge opens it with `--app --start-fullscreen`, so there is no address bar and no tabs. The model's sentence goes in as data and is never inserted as HTML. A test feeds it a nudge containing `</script>` and checks that the page does not break.

**Tests.** There are 98 tests, including one that blocks every network socket and still runs the outage path to the end. I also broke the guard on purpose 8 times (wider tolerances, checks removed), and a test failed every time.

## Why Does Open Innovation Matter?

Because the network dies with the light.

When NEPA takes light, my router is off until someone starts the gen. A cloud API is unreachable at the exact moment this tool needs to speak. A model on my laptop answers in 4 seconds with no signal. Another reason was not needed.

It also costs nothing per outage, which matters when outages happen every day. And because Ollama and the model are open, I could see why the first real call failed: an idle model unloads after 5 minutes, and I could change that setting. With a closed API, a timeout is just a timeout.

## My Agent Session

[DANIEL: decide. This was built with Claude Code (spec, code, tests, the timing test, the bug diagnosis). Either embed the DevRelay session or say so plainly here in one line. About 30 entries already embed one.]

## Prize Categories

- **Best Use of Gemma.** Gemma 4 E2B (QAT) runs locally through Ollama, offline, on a CPU-only laptop. It is the only part of the system that writes text, and the guard limits it to what a small model does well.

[DANIEL: closing line in your voice, or cut this.]
