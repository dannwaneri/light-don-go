"""Show the message once: console, plus a full-screen page (or a Windows toast as fallback)."""
import json
import os
import subprocess
import sys
from pathlib import Path

TAKEOVER_TEMPLATE = Path(__file__).with_name("takeover.html")
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

TOAST_PS = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$x = $t.GetElementsByTagName('text')
$x.Item(0).AppendChild($t.CreateTextNode($env:LDG_TITLE)) > $null
$x.Item(1).AppendChild($t.CreateTextNode($env:LDG_BODY)) > $null
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($t))
"""


def toast(title, body):
    if sys.platform != "win32":
        return False
    import os
    env = dict(os.environ, LDG_TITLE=title, LDG_BODY=body)
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", TOAST_PS],
                       env=env, timeout=15, capture_output=True, check=True)
        return True
    except Exception:
        return False


def takeover_data(rec, stretch_s=60):
    f = rec["facts"]
    lines = rec["message"].splitlines()
    return {
        "situation": rec["model_view"]["situation"],
        "facts_line": lines[0],
        "nudge": rec["final"],
        "close_line": lines[-1],
        "battery_pct": f.battery_pct,
        "low_battery": any(l.startswith("Battery ") for l in lines),
        "stretch_s": stretch_s,
    }


def render_takeover(data):
    """Inject the data as JSON. '</' is escaped so model text can never close the script tag."""
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TAKEOVER_TEMPLATE.read_text(encoding="utf-8")
    start = html.index("/*__DATA__*/")
    end = html.index(";", start)
    return html[:start] + blob + html[end:]


def find_browser():
    return next((b for b in BROWSERS if os.path.exists(b)), None)


def takeover(rec, out="cache/takeover.html", stretch_s=60, launch=True):
    """Write the page and open it full screen. Returns True if a browser was launched."""
    p = Path(out).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_takeover(takeover_data(rec, stretch_s)), encoding="utf-8")
    if not launch:
        return False
    browser = find_browser()
    if browser is None:
        return False
    profile = p.parent / "browser-takeover"
    try:
        subprocess.Popen([browser, f"--app={p.as_uri()}", "--start-fullscreen",
                          f"--user-data-dir={profile}", "--no-first-run",
                          "--no-default-browser-check"])
        return True
    except OSError:
        return False


def show(message, use_toast=True):
    bar = "=" * 60
    print(f"\n{bar}\n  LIGHT DON GO\n\n  {message.replace(chr(10), chr(10) + '  ')}\n{bar}\n", flush=True)
    if use_toast:
        toast("Light don go", message)
