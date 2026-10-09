"""Windows toast notification (with the default 'ting' sound) so the user knows when a long run needs them.

Uses the built-in WinRT toast API through Windows PowerShell 5.1 — nothing to install.
Never raises: a failed notification must not stop the pipeline.
"""
import os
import subprocess
import sys

# PowerShell's own AppUserModelID: lets an unregistered script show toasts
_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
# title/message come in through env vars, so no quoting/escaping of user text inside the script
_SCRIPT = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$text = $xml.GetElementsByTagName('text')
$text.Item(0).AppendChild($xml.CreateTextNode($env:AVF_TOAST_TITLE)) > $null
$text.Item(1).AppendChild($xml.CreateTextNode($env:AVF_TOAST_MESSAGE)) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{_APP_ID}').Show($toast)
"""


def notify(title, message):
    """Show a toast in the background (does not wait); print it too so the log has the same text."""
    print(f"  [thông báo] {title}: {message}")
    if sys.platform != "win32":
        return
    env = {**os.environ, "AVF_TOAST_TITLE": title, "AVF_TOAST_MESSAGE": message}
    try:
        subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    except OSError as e:
        print(f"  (không hiện được thông báo: {e})")


if __name__ == "__main__":  # quick manual test: python scripts/desktop_notification.py
    notify("AI Video Factory", "Thử thông báo — nếu bạn thấy và nghe 'ting' là được.")
