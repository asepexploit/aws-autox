"""Patchright/Playwright browser launch — follows Patchright official best practices.

Key rules from Patchright README & community:
1. Use launch_persistent_context (NOT launch + new_context)
2. Use channel="chrome" (real Chrome, not bundled Chromium)
3. headless=False (headed mode)
4. no_viewport=True (use real window size, don't fake viewport)
5. Do NOT set custom user_agent or extra HTTP headers (detectable mismatch)
6. Proxy via context proxy= param
7. Init scripts for extra stealth are still fine
"""

import os
import shutil
import tempfile

from config import PROXY_HOST, PROXY_USER, PROXY_PASS

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--enforce-webrtc-ip-permission-check",
    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--disable-webrtc",
    "--disable-infobars",
    "--lang=en-US",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-default-apps",
    "--disable-component-update",
    "--disable-background-networking",
    "--disable-sync",
    "--metrics-recording-only",
    "--disable-features=TranslateUI",
    "--mute-audio",
]

STEALTH_INIT_SCRIPT = """
    // --- Block WebRTC leak — prevent local/real IP from leaking via ICE candidates ---
    const _RTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
    if (_RTCPeerConnection) {
        const _origPC = _RTCPeerConnection.prototype.createOffer;
        window.RTCPeerConnection = function(config) {
            if (config && config.iceServers) { config.iceServers = []; }
            const pc = new _RTCPeerConnection(config);
            const _addCandidate = pc.addIceCandidate.bind(pc);
            pc.addIceCandidate = () => Promise.resolve();
            return pc;
        };
        Object.assign(window.RTCPeerConnection, _RTCPeerConnection);
        window.RTCPeerConnection.prototype = _RTCPeerConnection.prototype;
        if (window.webkitRTCPeerConnection) {
            window.webkitRTCPeerConnection = window.RTCPeerConnection;
        }
    }

    // --- navigator.webdriver ---
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // --- navigator.languages: samakan dengan Accept-Language header "en-US,en;q=0.9"
    // Real Chrome single-language user selalu punya ["en-US", "en"], bukan ["en-US"] saja
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

    // --- Fix UA mismatch: userAgent string bilang Windows NT 10.0 tapi userAgentData bilang Windows 11
    // Samakan platform version di userAgentData supaya konsisten dengan UA string Chrome modern
    if (navigator.userAgentData) {
        const _uaData = navigator.userAgentData;
        const _getHighEntropyValues = _uaData.getHighEntropyValues.bind(_uaData);
        Object.defineProperty(navigator, 'userAgentData', {
            get: () => new Proxy(_uaData, {
                get(target, prop) {
                    if (prop === 'getHighEntropyValues') {
                        return async (hints) => {
                            const vals = await _getHighEntropyValues(hints);
                            // Samakan platformVersion supaya konsisten (Windows 11 = 15.0.0+)
                            if (vals.platformVersion !== undefined) {
                                vals.platformVersion = '15.0.0';
                            }
                            return vals;
                        };
                    }
                    return Reflect.get(target, prop);
                }
            })
        });
    }

    // --- permissions API ---
    const originalQuery = window.navigator.permissions?.query;
    if (originalQuery) {
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
    }

    // --- CDP artifact cleanup ---
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


_SESSION_PATHS = [
    "Default/Sessions",
    "Default/Session Storage",
    "Default/Service Worker",
    "Default/Cookies",
    "Default/Cookies-journal",
    "Default/History",
    "Default/History-journal",
    "Default/Login Data",
    "Default/Login Data-journal",
    "Default/Login Data For Account",
    "Default/Login Data For Account-journal",
    "Default/Local Storage",
    "Default/Network",
    "Default/DIPS",
]


def _wipe_session(user_data_dir: str) -> None:
    """Hapus session/cookie/history setelah browser ditutup."""
    for subdir in _SESSION_PATHS:
        p = os.path.join(user_data_dir, subdir)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass


async def launch(pw, proxy_port: int | None = None, timezone: str = "America/Chicago"):
    """Launch stealth browser using Patchright best practices.

    Returns (context, page). Context acts as both browser & context
    when using launch_persistent_context.
    """
    proxy_config = None
    if proxy_port:
        proxy_config = {
            "server": f"http://{PROXY_HOST}:{proxy_port}",
            "username": PROXY_USER,
            "password": PROXY_PASS,
        }

    user_data_dir = os.path.join(tempfile.gettempdir(), f"patchright_profile_{proxy_port or 'direct'}")
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    context = await pw.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="chrome",
        headless=False,
        no_viewport=True,
        proxy=proxy_config,
        locale="en-US",
        timezone_id=timezone,
        args=STEALTH_ARGS,
        chromium_sandbox=True,
        downloads_path=downloads_dir,
        accept_downloads=True,
    )

    await context.add_init_script(STEALTH_INIT_SCRIPT)

    # Persistent context already has one page open
    if context.pages:
        page = context.pages[0]
    else:
        page = await context.new_page()

    return context, context, page
