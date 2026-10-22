"""TempMail API client (panelmr4sep)."""

import json
import re
import urllib.parse
import urllib.request

from config import PANEL_URL, DEVICE_SECRET


def _call(action: str, params: dict | None = None) -> dict:
    base = PANEL_URL.rstrip("/")
    qp = {"action": action}
    if params:
        qp.update(params)
    url = f"{base}/api/ext/tempmail.php?{urllib.parse.urlencode(qp)}"
    req = urllib.request.Request(
        url, headers={"X-Device-Secret": DEVICE_SECRET}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "API error"))
    return data


def create_email(prefer_domain: str = "", exclude: str = "") -> dict:
    """Create a random temp email. Returns full API response."""
    params = {}
    if prefer_domain:
        params["prefer_domain"] = prefer_domain
    if exclude:
        params["exclude_domains"] = exclude
    return _call("quick_email", params)


def check_inbox(email: str, account_token: str = "", ts: str = "") -> list[dict]:
    """Return list of messages in the inbox."""
    params = {"email": email}
    if account_token:
        params["account_token"] = account_token
    if ts:
        params["ts"] = ts
    data = _call("inbox", params)
    return data.get("messages", [])


def poll_otp(email: str, account_token: str, ts: str, interval: int, max_wait: int) -> str | None:
    """Poll inbox until a 6-digit OTP is found. Returns OTP or None."""
    import time

    elapsed = 0
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        try:
            data = _call("poll_otp", {
                "email": email,
                "account_token": account_token,
                "ts": ts,
            })
            if data.get("found"):
                return data["otp"]
        except Exception as exc:
            # Fallback: try inbox + manual parse
            try:
                messages = check_inbox(email, account_token, ts)
                for msg in messages:
                    combined = (
                        msg.get("subject", "")
                        + " "
                        + (msg.get("body_preview", "") or msg.get("body", "") or "")
                    )
                    match = re.search(r"\b(\d{6})\b", combined)
                    if match:
                        return match.group(1)
            except Exception:
                pass
            print(f"  Poll error: {exc}")
        print(f"  Waiting for OTP... ({elapsed}s/{max_wait}s)")
    return None
