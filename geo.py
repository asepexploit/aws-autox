"""IP geolocation lookup through proxy."""

import json
import urllib.request

from config import PROXY_HOST, PROXY_USER, PROXY_PASS


def lookup(proxy_port: int) -> dict:
    """Return {"query": ip, "regionName": ..., "timezone": ...}."""
    try:
        proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{proxy_port}"
        handler = urllib.request.ProxyHandler({"http": proxy_url})
        opener = urllib.request.build_opener(handler)
        req = urllib.request.Request(
            "http://ip-api.com/json/?fields=regionName,timezone,query",
            headers={"User-Agent": "curl/8.0"},
        )
        with opener.open(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"  Geo lookup failed ({exc}), default US/Central")
        return {
            "regionName": "Texas",
            "timezone": "America/Chicago",
            "query": "?",
        }
