"""One call to the local model. No loops here: the caller decides about the single retry."""
import json
import urllib.error
import urllib.request
from pathlib import Path

PROMPT = (Path(__file__).with_name("prompt.txt")).read_text(encoding="utf-8")


class ModelUnavailable(RuntimeError):
    pass


def retry_hint(guard_result):
    """Turn a failed guard check into one line for the single retry."""
    parts = []
    if guard_result.bad:
        parts.append("Your last sentence used numbers: "
                     + ", ".join(guard_result.bad) + ". Use no numbers at all.")
    if "off_topic" in guard_result.reasons:
        parts.append("Your last sentence mentioned light or the generator. Do not.")
    if any(r.startswith("too_long") for r in guard_result.reasons):
        parts.append("Your last sentence was too long. Use 20 words or fewer.")
    return " ".join(parts)


def build_prompt(view, retry=""):
    return PROMPT.format(activity=view["activity"], situation=view["situation"],
                         retry=retry or "")


def _post(url, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def clean(text):
    line = next((l for l in text.strip().splitlines() if l.strip()), "")
    return line.strip().strip('"“”').strip()


def write(view, cfg, retry="", post=_post):
    body = {
        "model": cfg.model,
        "prompt": build_prompt(view, retry),
        "stream": False,
        "think": False,
        "options": {"temperature": 0.7, "num_predict": 60},
    }
    try:
        d = post(f"{cfg.ollama_url}/api/generate", body, cfg.model_timeout_s)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise ModelUnavailable(str(e)) from e
    text = clean(d.get("response", ""))
    if not text:
        raise ModelUnavailable("empty response")
    return text


def warm_up(cfg, post=_post):
    """Load the model into memory so the first real outage is not a cold call (~14 s)."""
    try:
        post(f"{cfg.ollama_url}/api/generate",
             {"model": cfg.model, "prompt": "ok", "stream": False, "think": False,
              "options": {"num_predict": 1}}, 120)
        return True
    except Exception:
        return False
