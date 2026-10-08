import time

from light_don_go import writer
from light_don_go.config import Config
from light_don_go.guard import GuardResult

VIEW = {"place": "Port Harcourt", "situation": "dry daylight", "activity": "walk", "battery_pct": 41}


def test_unreachable_model_raises_within_timeout():
    cfg = Config(ollama_url="http://127.0.0.1:9", model_timeout_s=3)
    t0 = time.perf_counter()
    try:
        writer.write(VIEW, cfg)
        raised = False
    except writer.ModelUnavailable:
        raised = True
    assert raised and time.perf_counter() - t0 <= 20


def test_clean_takes_first_line_without_quotes():
    assert writer.clean('\n"Go outside now."\nExtra line') == "Go outside now."


def test_retry_hint_names_numbers_and_length():
    h = writer.retry_hint(GuardResult(False, ["3 hours"], ["duration", "too_long:30", "off_topic"]))
    assert "3 hours" in h and "20 words" in h and "generator" in h


def test_prompt_has_facts_and_retry():
    p = writer.build_prompt(VIEW, "Do not use 3 hours.")
    assert "walk" in p and "dry daylight" in p and "Do not use 3 hours." in p


def test_write_and_warm_up_ask_ollama_to_keep_model_loaded():
    seen = []

    def post(url, body, timeout):
        seen.append(body)
        return {"response": "Abeg close am."}
    cfg = Config()
    writer.write(VIEW, cfg, post=post)
    writer.warm_up(cfg, post=post)
    assert [b["keep_alive"] for b in seen] == [-1, -1]
