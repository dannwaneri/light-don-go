---
title: When NEPA takes light, my laptop tells me to go outside before I on the gen
published: false
tags: devchallenge, hf26challenge, gemma, opensource
cover_image: https://raw.githubusercontent.com/dannwaneri/light-don-go/main/docs/screenshots/takeover-rain.png
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

In Port Harcourt, the light goes and the room changes in about two seconds. The fan stops. The router dies. The laptop drops to battery. Then somebody shouts "on the gen!"

I used to just sit there. Phone on mobile data, laptop on battery, waiting for the gen to come on so I could keep working.

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

**Words you may not know** (Nigerian English and Pidgin):

| Word | Meaning |
|---|---|
| NEPA | What Nigerians still call the power company (the old National Electric Power Authority). "NEPA takes light" means the grid power goes off. |
| Light don go | "The power is gone." |
| Gen, "on the gen" | The petrol generator most homes start by hand when the grid fails. "On the gen" means start it. |
| Hold the gen | Keep the generator off. "₦1,500 saved every hour e rest" means each hour it stays off saves ₦1,500 of petrol. |
| Abeg · waka · close am · fit | Please · walk · close it · may ("rain fit start" = rain may start) |
| You self don try | "You have done well." |
| Mineral · kiosk · junction | Soft drink · small roadside shop · the street corner where food sellers sit |
| WAT | West Africa Time, UTC+1 |

## Demo

{% youtube Zr-YILDu6JI %}

Watch on YouTube: https://youtu.be/Zr-YILDu6JI

Real outages so far, from `logs/outages.jsonl` (8 and 9 October 2026, WAT):

| Time | Event | What the tool did |
|---|---|---|
| 12:23 | NEPA cut | Rain path, indoor activity. Gemma **timed out**; fallback sentence shown |
| 12:25 | Power back after 123 s | Logged (the gen) |
| 12:31 | NEPA cut again | Gemma: *"Abeg shut that laptop, waka go stand by the window stretch back and legs, rain dey down."* Passed the guard first try |
| 12:34 | Power back after 225 s | Logged |
| 12:53 | NEPA cut | First cut with the full-screen page. Gemma: *"Abeg shut that laptop, walk to the kiosk for cold mineral and come back quick."* Passed first try. Facts line: rain around 15:00, about 2 hours left |
| 13:34 | NEPA cut, laptop asleep | Timed out, fallback logged. The Windows event log shows the laptop was in Modern Standby: it woke for a moment at the cut, went back to sleep mid-call, and woke again at 13:56. The model was still loaded. Nobody was at the screen |
| 9 Oct, 07:33 | NEPA cut | Gemma: *"Abeg shut that laptop, walk to the kiosk find cold mineral and come back quick."* Passed first try |

**What I did when it told me to go.** I closed my laptop, took a walk outside in my neighbourhood in Port Harcourt, visited my cousins and played with their children. That was the 07:33 cut on 9 October. The light came back at about 12:05.

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

**What the guard can't do.** It checks numbers and topic, not sense. In one test run Gemma wrote "watch the rain inside the phone", and it passed. A bigger model would make fewer sentences like that, but it would not run on this laptop. I chose the small model, and I accept that one of its sentences will sometimes be odd.

**The bug a real outage found.** At 12:23 the light went, the tool caught it, and Gemma timed out. I measured before changing anything. `ollama ps` showed that the model had just been loaded, by the request that failed. Ollama unloads an idle model after 5 minutes. My warm-up had run at 11:53, so at 12:23 the tool hit a cold start, on battery, and took more than 20 s. The fix is one setting: `keep_alive: -1`, which keeps Gemma in RAM (3.9 GB of my 15.7). At the next cut, at 12:31, Gemma answered first time. One later cut, at 13:34, also timed out, but the cause was different: the laptop was asleep (Windows Modern Standby). I checked the event log before blaming the fix.

So the defaults broke the one promise the tool makes, which is to work when the light goes. I would not have found that in a simulation.

**The page.** One HTML file with the outage data written in as JSON. Edge opens it with `--app --start-fullscreen`, so there is no address bar and no tabs. The model's sentence goes in as data and is never inserted as HTML. A test feeds it a nudge containing `</script>` and checks that the page does not break.

**Tests.** There are 98 tests, including one that blocks every network socket and still runs the outage path to the end. I also broke the guard on purpose 8 times (wider tolerances, checks removed), and a test failed every time.

## Why Does Open Innovation Matter?

Because the network dies with the light.

When NEPA takes light, my router is off until someone starts the gen. A cloud API is unreachable at the exact moment this tool needs to speak. A model on my laptop answers in 4 seconds with no signal. Another reason was not needed.

It also costs nothing per outage, which matters when outages happen every day. And because Ollama and the model are open, I could see why the first real call failed: an idle model unloads after 5 minutes, and I could change that setting. With a closed API, a timeout is just a timeout.

## Prize Categories

- **Best Use of Gemma.** Gemma 4 E2B (QAT) runs locally through Ollama, offline, on a CPU-only laptop. It is the only part of the system that writes text, and the guard limits it to what a small model does well.

The tool's best result so far isn't in the logs. It's a morning with my cousins' children that I would have spent waiting for the gen.
