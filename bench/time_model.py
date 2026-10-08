"""Time a local Ollama model on the real Light-don-go prompt.

Usage: python bench/time_model.py [model] [runs]
Run 1 includes model load (cold). Runs 2..N are warm.
Pass rule from SPEC review checkpoint: warm wall time <= 20 s.
"""
import json
import sys
import time
import urllib.request

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma4:e2b-it-qat"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 5

FACTS = {
    "place": "Port Harcourt",
    "time_now": "16:30",
    "dry_minutes_left": 120,
    "rain_starts_at": "18:30",
    "daylight_minutes_left": 75,
    "sunset_at": "17:45",
    "temp_c": 29,
    "battery_pct": 41,
    "naira_saved_per_hour": 1500,
    "activity": "walk to the junction and buy roasted plantain and fish",
}

PROMPT = (
    "NEPA just took light. Write ONE sentence, 25 words or fewer, in Nigerian English "
    "with a light Pidgin flavour, telling the reader to go outside now and do the activity "
    "before they on the generator. Use ONLY numbers that appear in these facts. "
    "Do not invent any number. Do not add anything after the sentence.\n"
    f"FACTS: {json.dumps(FACTS)}"
)


def call():
    body = json.dumps({
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.7, "num_predict": 60},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    wall = time.perf_counter() - t0
    tps = d["eval_count"] / (d["eval_duration"] / 1e9) if d.get("eval_duration") else 0
    return wall, d.get("load_duration", 0) / 1e9, d.get("eval_count", 0), tps, d["response"].strip()


if __name__ == "__main__":
    print(f"model={MODEL} runs={RUNS}")
    warm = []
    for i in range(1, RUNS + 1):
        wall, load, n, tps, text = call()
        if i > 1:
            warm.append(wall)
        print(f"run {i}: wall={wall:.1f}s load={load:.1f}s tokens={n} decode={tps:.1f} t/s")
        print(f"   -> {text}")
    if warm:
        worst = max(warm)
        print(f"warm: min={min(warm):.1f}s max={worst:.1f}s  PASS(<=20s)={worst <= 20}")
