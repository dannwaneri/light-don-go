"""Show the message once: console, plus a Windows toast if available."""
import subprocess
import sys

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


def show(message, use_toast=True):
    bar = "=" * 60
    print(f"\n{bar}\n  LIGHT DON GO\n\n  {message.replace(chr(10), chr(10) + '  ')}\n{bar}\n", flush=True)
    if use_toast:
        toast("Light don go", message)
