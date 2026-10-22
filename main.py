"""
AWS Builder ID signup automation via Patchright/Playwright (stealth).

Usage:
    python main.py --proxy 10000                        # 1 account
    python main.py --proxy 10000 --count 3              # 3 accounts sequential
    python main.py --proxy 10000 --count 6 --threads 3  # 6 accounts, 3 parallel
    python main.py --proxy 10000 --count 3 --skip-preflight

Requires (pick one):
    pip install patchright && python -m patchright install chromium   (RECOMMENDED)
    pip install playwright && python -m playwright install chromium   (fallback)
"""

import argparse
import asyncio
import os
import random
import threading

import flow

MAX_OTP_RETRIES = 3
BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), "blacklisted_domains.txt")
SUCCESS_DOMAINS_FILE = os.path.join(os.path.dirname(__file__), "successful_domains.txt")
USED_PROXIES_FILE = os.path.join(os.path.dirname(__file__), "used_proxies.txt")

_blacklist_lock = threading.Lock()
_success_lock = threading.Lock()
_proxy_lock = threading.Lock()


def _load_blacklist() -> set[str]:
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    with open(BLACKLIST_FILE, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def _save_blacklist(domains: set[str]):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        for d in sorted(domains):
            f.write(d + "\n")


def _add_to_blacklist(blacklisted: set[str], domain: str):
    with _blacklist_lock:
        blacklisted.add(domain)
        _save_blacklist(blacklisted)


def _load_used_proxies() -> set[int]:
    if not os.path.exists(USED_PROXIES_FILE):
        return set()
    with open(USED_PROXIES_FILE, encoding="utf-8") as f:
        result = set()
        for line in f:
            line = line.strip()
            if line.isdigit():
                result.add(int(line))
        return result


def _save_used_proxy(port: int):
    with _proxy_lock:
        existing = _load_used_proxies()
        if port in existing:
            return
        with open(USED_PROXIES_FILE, "a", encoding="utf-8") as f:
            f.write(str(port) + "\n")
        print(f"  [used_proxies] Port {port} saved")


def _load_success_domains() -> list[str]:
    if not os.path.exists(SUCCESS_DOMAINS_FILE):
        return []
    with open(SUCCESS_DOMAINS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _save_success_domain(domain: str):
    with _success_lock:
        existing = _load_success_domains()
        if domain not in existing:
            with open(SUCCESS_DOMAINS_FILE, "a", encoding="utf-8") as f:
                f.write(domain + "\n")
            print(f"  [success_domains] Saved: {domain}")


def _get_exclude(blacklisted: set[str]) -> str:
    with _blacklist_lock:
        return ",".join(sorted(blacklisted))


def _next_port(current_port: int | None, used_proxies: set[int]) -> int | None:
    if not current_port:
        return None
    next_port = current_port + 1
    while next_port in used_proxies:
        next_port += 1
    return next_port


def _mark_and_rotate(tag: str, current_port: int, used_proxies: set[int], reason: str) -> int:
    """Mark current_port as used, save to file, return next available port."""
    _save_used_proxy(current_port)
    with _proxy_lock:
        used_proxies.add(current_port)
    next_port = _next_port(current_port, used_proxies)
    print(f"  {tag} Port {current_port} marked used ({reason}) → rotating to {next_port}.")
    return next_port


async def run_one_account(pw, account_num: int, total: int, port: int | None,
                          otpmurah_key: str, skip_preflight: bool,
                          blacklisted: set[str],
                          used_proxies: set[int]) -> dict:
    """Run signup for a single account with OTP retry + proxy rotation logic."""
    tag = f"[#{account_num}/{total}]"
    print(f"\n{'#'*60}")
    print(f"  {tag} ACCOUNT  (port {port or 'direct'})")
    print(f"{'#'*60}")

    current_port = port
    result = None
    otp_attempt = 0
    run_count = 0
    while True:
        run_count += 1
        exclude = _get_exclude(blacklisted)

        # On last OTP retry: prefer a domain that delivered OTP before
        prefer_domain = ""
        if otp_attempt == MAX_OTP_RETRIES - 1:
            success_doms = _load_success_domains()
            usable = [d for d in success_doms if d not in blacklisted]
            if usable:
                prefer_domain = usable[0]
                print(f"\n  {tag} Last OTP retry — preferring proven domain: {prefer_domain}")

        if run_count > 1:
            print(f"\n  {tag} Retry #{run_count - 1} — new email, new Chrome (port {current_port or 'direct'})")
            if exclude:
                print(f"  {tag} Blacklisted: {exclude}")
            delay = random.randint(5, 15)
            print(f"  {tag} Waiting {delay}s...")
            await asyncio.sleep(delay)

        result = await flow.run(
            pw,
            proxy_port=current_port,
            otpmurah_key=otpmurah_key,
            skip_preflight=skip_preflight,
            exclude_domains=exclude,
            prefer_domain=prefer_domain,
        )

        # OTP succeeded — save domain (even if later steps failed)
        otp_dom = result.get("otp_domain", "")
        if otp_dom:
            _save_success_domain(otp_dom)

        if result.get("error") == "otp_timeout":
            bad = result.get("blacklist_domain", "")
            if bad:
                _add_to_blacklist(blacklisted, bad)
                print(f"  {tag} Domain '{bad}' blacklisted (saved)")
            otp_attempt += 1
            if otp_attempt >= MAX_OTP_RETRIES:
                print(f"  {tag} OTP failed {MAX_OTP_RETRIES}x — giving up.")
                break
            continue

        err_str = result.get("error", "")
        _proxy_error = current_port and (
            err_str == "payment_required"
            or any(k in err_str for k in ("ERR_SSL", "ERR_PROXY", "ERR_TUNNEL", "net::"))
        )
        if _proxy_error:
            current_port = _mark_and_rotate(tag, current_port, used_proxies, err_str)
            otp_attempt = 0
            continue

        break  # ok or other error

    return result


async def main():
    parser = argparse.ArgumentParser(
        description="AWS Builder ID signup via Patchright/Playwright"
    )
    parser.add_argument(
        "--proxy", "-p", type=int,
        help="Proxy start port (e.g. 10000). Each account uses next port.",
    )
    parser.add_argument(
        "--count", "-c", type=int, default=1,
        help="Number of accounts to create (default: 1)",
    )
    parser.add_argument(
        "--threads", "-t", type=int, default=1,
        help="Parallel threads / browser instances (default: 1)",
    )
    parser.add_argument(
        "--otpmurah", type=str, default="",
        help="OTPMurah API key for real phone number rental",
    )
    parser.add_argument(
        "--skip-preflight", action="store_true",
        help="Skip bot-test sites (sannysoft/creepjs) — reduces detection risk",
    )
    parser.add_argument(
        "--dev", action="store_true",
        help="Dev mode: buka browser + preflight saja, tidak jalankan signup flow",
    )
    args = parser.parse_args()

    threads = min(args.threads, args.count)

    try:
        from patchright.async_api import async_playwright
        print("[engine] Using Patchright (stealth fork)")
    except ImportError:
        from playwright.async_api import async_playwright
        print("[engine] Using Playwright (install patchright for better stealth)")

    if threads > 1:
        print(f"[mode] Parallel: {threads} threads, {args.count} accounts")
    else:
        print(f"[mode] Sequential: {args.count} account(s)")

    if args.dev:
        import tempfile
        import browser as _browser
        port = args.proxy
        print(f"[dev] Launching browser only (port {port or 'direct'})...")
        async with async_playwright() as pw:
            _bro, _, _page = await _browser.launch(pw, port)
            print("[dev] Browser open. Tutup manual untuk exit.")
            try:
                await _page.wait_for_timeout(999_999_999)
            except Exception:
                pass
            finally:
                await _bro.close()
                _browser._wipe_session(
                    __import__("os").path.join(tempfile.gettempdir(), f"patchright_profile_{port or 'direct'}")
                )
        return

    blacklisted = _load_blacklist()
    if blacklisted:
        print(f"[blacklist] Loaded {len(blacklisted)} domain(s):")
        for d in sorted(blacklisted):
            print(f"  - {d}")

    used_proxies = _load_used_proxies()
    if used_proxies:
        print(f"[used_proxies] Loaded {len(used_proxies)} used port(s): {sorted(used_proxies)}")

    # Build job list: (account_num, proxy_port) — skip already-used proxies
    jobs = []
    port_cursor = args.proxy
    for i in range(args.count):
        if args.proxy:
            while port_cursor in used_proxies:
                print(f"[used_proxies] Skipping port {port_cursor} (already used)")
                port_cursor += 1
            port = port_cursor
            port_cursor += 1
        else:
            port = None
        jobs.append((i + 1, port))

    results = []

    async with async_playwright() as pw:
        if threads <= 1:
            # Sequential
            for account_num, port in jobs:
                result = await run_one_account(
                    pw, account_num, args.count, port,
                    args.otpmurah, args.skip_preflight, blacklisted, used_proxies,
                )
                results.append(result)

                if account_num < args.count:
                    delay = random.randint(15, 45)
                    print(f"\nWaiting {delay}s before next account...")
                    await asyncio.sleep(delay)
        else:
            # Parallel — process in batches of `threads`
            for batch_start in range(0, len(jobs), threads):
                batch = jobs[batch_start:batch_start + threads]

                if batch_start > 0:
                    delay = random.randint(10, 25)
                    print(f"\n{'='*60}")
                    print(f"  Batch done. Waiting {delay}s before next batch...")
                    print(f"{'='*60}")
                    await asyncio.sleep(delay)

                print(f"\n{'='*60}")
                print(f"  BATCH: accounts {batch[0][0]}-{batch[-1][0]}"
                      f" ({len(batch)} parallel)")
                print(f"{'='*60}")

                # Stagger start times so browsers don't all launch at once
                async def staggered(idx, account_num, port):
                    if idx > 0:
                        stagger = random.uniform(3, 8) * idx
                        await asyncio.sleep(stagger)
                    return await run_one_account(
                        pw, account_num, args.count, port,
                        args.otpmurah, args.skip_preflight, blacklisted, used_proxies,
                    )

                tasks = [
                    asyncio.create_task(staggered(idx, num, port))
                    for idx, (num, port) in enumerate(batch)
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for br in batch_results:
                    if isinstance(br, Exception):
                        results.append({"ok": False, "error": str(br), "email": "?"})
                    else:
                        results.append(br)

    # ── Summary ──
    ok_count = sum(1 for r in results if r.get("ok"))
    print(f"\n\n{'='*60}")
    print(f"  RESULTS: {ok_count}/{len(results)} successful")
    print(f"{'='*60}")
    for r in results:
        if r.get("ok"):
            status = "OK"
        elif r.get("error") == "payment_required":
            status = "SKIP"
        else:
            status = "FAIL"
        email = r.get("email", "?")
        err = f" — {r['error']}" if r.get("error") else ""
        print(f"  [{status}] {email}{err}")

    if blacklisted:
        print(f"\n  Blacklisted domains ({len(blacklisted)}):")
        for d in sorted(blacklisted):
            print(f"    - {d}")


if __name__ == "__main__":
    asyncio.run(main())
