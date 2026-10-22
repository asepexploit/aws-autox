"""OTPMurah.id API client for renting Indonesian phone numbers."""

import json
import urllib.request


def _call(api_key: str, action: str, params: dict | None = None) -> dict:
    base = "https://otpmurah.id/api"
    qs = f"api_key={api_key}&action={action}"
    if params:
        for k, v in params.items():
            qs += f"&{k}={v}"
    req = urllib.request.Request(f"{base}?{qs}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_balance(api_key: str) -> dict:
    return _call(api_key, "getBalance")


def rent_number(api_key: str, service: str = "am", country: str = "6") -> dict:
    """Rent a number for the given service. Returns activation data."""
    return _call(api_key, "getNumber", {"service": service, "country": country})


def check_sms(api_key: str, activation_id: str) -> dict:
    """Check if SMS has arrived for an activation."""
    return _call(api_key, "getStatus", {"id": activation_id})


def finish(api_key: str, activation_id: str) -> dict:
    """Mark activation as finished (SMS received & used)."""
    return _call(api_key, "setStatus", {"id": activation_id, "status": "6"})


def cancel(api_key: str, activation_id: str) -> dict:
    """Cancel activation for refund."""
    return _call(api_key, "cancelActivation", {"id": activation_id})
