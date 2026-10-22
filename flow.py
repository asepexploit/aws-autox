"""7-step AWS Builder ID signup flow."""

import asyncio
import os
import random
import tempfile

import browser
import datagen
import geo
import human
import tempmail
from config import AWS_PASSWORD, OTP_POLL_INTERVAL, OTP_MAX_WAIT, SIGNUP_URL

DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")


async def run(pw, proxy_port: int | None = None, otpmurah_key: str = "",
              skip_preflight: bool = False, exclude_domains: str = "",
              prefer_domain: str = "") -> dict:
    """Execute full signup. Returns result dict."""

    # ── Geo lookup ──
    tz = "America/Chicago"
    proxy_ip = "direct"
    otp_domain_value = ""
    if proxy_port:
        print(f"\n[geo] Looking up IP for port {proxy_port}...")
        g = geo.lookup(proxy_port)
        proxy_ip = g.get("query", "?")
        tz = g.get("timezone") or "America/Chicago"
        print(f"  IP: {proxy_ip}  Region: {g.get('regionName', '?')}  TZ: {tz}")

    # ── Step 1: Create temp email ──
    print("\n[1/7] Creating temp email...")
    try:
        email_data = tempmail.create_email(prefer_domain=prefer_domain, exclude=exclude_domains)
    except Exception as exc:
        print(f"  Tempmail API error: {exc}")
        return {"ok": False, "error": f"tempmail_error: {exc}", "email": "?"}
    email = email_data["email"]
    account_token = email_data.get("account_token", "")
    email_ts = email_data.get("ts", "")
    print(f"  Email: {email}")

    # ── Generate identity ──
    name = datagen.random_name()
    addr = datagen.random_address()
    phone = datagen.random_phone()
    print(f"  Name: {name}")
    print(f"  Address: {addr['street']}, {addr['city']} {addr['state']}")
    print(f"  Phone: {phone}")

    # ── OTPMurah: rent number ──
    sewa = None
    if otpmurah_key:
        try:
            import otpmurah
            print("\n[otp] Renting phone number from OTPMurah...")
            data = otpmurah.rent_number(otpmurah_key)
            sewa_phone = data.get("phone_number") or data.get("phone") or ""
            sewa_id = data.get("activation_id") or data.get("id") or ""
            if sewa_phone and sewa_id:
                sewa = {"id": sewa_id, "phone": sewa_phone}
                raw = sewa_phone.lstrip("1")
                phone = raw
                print(f"  Rented: +1{sewa_phone} (ID: {sewa_id})")
        except Exception as exc:
            print(f"  OTPMurah failed: {exc} — using random phone")

    # ── Launch browser ──
    bro, ctx, page = await browser.launch(pw, proxy_port, tz)

    # Auto-save downloads with original filename to ~/Downloads
    async def _on_download(download):
        filename = download.suggested_filename
        dest = os.path.join(DOWNLOADS_DIR, filename)
        await download.save_as(dest)
        print(f"  [download] Saved: {dest}")

    page.on("download", lambda dl: asyncio.ensure_future(_on_download(dl)))

    try:
        # ── Step 0: Preflight (optional — skipped by default to avoid leaving
        #    bot-test sites in the session's navigation history) ──
        if not skip_preflight:
            print("\n" + "=" * 60)
            print("  PREFLIGHT CHECK — IP / Fingerprint / Bot Detection")
            print("=" * 60)

            passed = 0
            warned = 0
            failed = 0

            # --- 0a: IP check ---
            print("\n  [0a] Checking browser IP...")
            await page.goto("https://api.ipify.org?format=json", timeout=30000)
            ip_json = await page.inner_text("body")
            try:
                browser_ip = __import__("json").loads(ip_json.strip()).get("ip", ip_json.strip())
            except Exception:
                browser_ip = ip_json.strip()

            ip_match = proxy_ip != "direct" and browser_ip == proxy_ip
            if proxy_ip == "direct":
                print(f"       IP: {browser_ip}  (no proxy)")
                warned += 1
            elif ip_match:
                print(f"       IP: {browser_ip}  [PASS — matches proxy]")
                passed += 1
            else:
                print(f"       IP: {browser_ip}  [FAIL — expected {proxy_ip}]")
                failed += 1

            # --- 0b: IP quality/type check ---
            print("\n  [0b] Checking IP type & reputation...")
            await page.goto(f"http://ip-api.com/json/{browser_ip}?fields=query,isp,org,as,proxy,hosting", timeout=15000)
            ip_info_text = await page.inner_text("body")
            try:
                ip_info = __import__("json").loads(ip_info_text.strip())
                is_proxy = ip_info.get("proxy", False)
                is_hosting = ip_info.get("hosting", False)
                isp = ip_info.get("isp", "?")
                org = ip_info.get("org", "?")
                print(f"       ISP: {isp}")
                print(f"       Org: {org}")
                if is_hosting:
                    print(f"       Type: DATACENTER/HOSTING  [WARN — residential preferred]")
                    warned += 1
                elif is_proxy:
                    print(f"       Type: KNOWN PROXY  [WARN — might be flagged]")
                    warned += 1
                else:
                    print(f"       Type: RESIDENTIAL  [PASS — best for stealth]")
                    passed += 1
            except Exception:
                print(f"       (could not parse IP info)")

            # --- 0c: Bot detection (SannySoft) ---
            print("\n  [0c] Bot detection test (SannySoft)...")
            await page.goto("https://bot.sannysoft.com/", timeout=30000)
            await asyncio.sleep(4)

            try:
                wd_result = await page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('table tr');
                        const results = {};
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const key = cells[0].textContent.trim();
                                const val = cells[1].textContent.trim();
                                const cls = cells[1].className || '';
                                results[key] = { value: val, pass: cls.includes('passed') };
                            }
                        }
                        return results;
                    }
                """)
                check_keys = [
                    "WebDriver", "WebDriver Advanced", "Chrome",
                    "Permissions", "User Agent", "WebGL Vendor",
                    "WebGL Renderer", "Broken Image", "outerDimensions",
                ]
                for key in check_keys:
                    if key in wd_result:
                        v = wd_result[key]
                        is_pass = v.get("pass", True)
                        label = "PASS" if is_pass else "FAIL"
                        if is_pass:
                            passed += 1
                        else:
                            failed += 1
                        val_short = v["value"][:60] if len(v.get("value", "")) > 60 else v.get("value", "")
                        print(f"       {key}: {val_short}  [{label}]")
            except Exception:
                print("       (could not read SannySoft results)")

            # --- 0d: CreepJS fingerprint ---
            print("\n  [0d] Fingerprint test (CreepJS)...")
            await page.goto("https://abrahamjuliot.github.io/creepjs/", timeout=60000)
            await asyncio.sleep(10)

            creep_grade = "?"
            try:
                grade_el = page.locator("#fingerprint-data .grade, .visitor-info .grade, [class*='grade']").first
                if await grade_el.is_visible(timeout=8000):
                    creep_grade = (await grade_el.inner_text()).strip()
            except Exception:
                pass

            if creep_grade != "?":
                gl = creep_grade.lower()
                if "high" in gl:
                    print(f"       Trust grade: {creep_grade}  [PASS — high trust]")
                    passed += 1
                elif "moderate" in gl:
                    print(f"       Trust grade: {creep_grade}  [OK — moderate trust]")
                    passed += 1
                elif "low" in gl:
                    print(f"       Trust grade: {creep_grade}  [WARN — low trust]")
                    warned += 1
                else:
                    import re as _re
                    pct = _re.search(r"(\d+)", creep_grade)
                    if pct and int(pct.group(1)) >= 50:
                        print(f"       Trust grade: {creep_grade}  [OK]")
                        passed += 1
                    elif pct:
                        print(f"       Trust grade: {creep_grade}  [WARN — low score]")
                        warned += 1
                    else:
                        print(f"       Trust grade: {creep_grade}  [INFO]")
                        passed += 1
            else:
                print(f"       Trust grade: (could not read)")

            # --- Summary ---
            print(f"\n  {'=' * 56}")
            total = passed + warned + failed
            print(f"  PREFLIGHT RESULT: {passed}/{total} PASS, {warned} WARN, {failed} FAIL")
            if failed == 0 and warned <= 2:
                print(f"  VERDICT: GOOD — safe to proceed")
            elif failed == 0:
                print(f"  VERDICT: OK — some warnings, might work")
            else:
                print(f"  VERDICT: RISKY — {failed} checks failed, might get detected")
            print(f"  {'=' * 56}")

            print("\n  Pausing 10s — review browser tabs...")
            await asyncio.sleep(10)
        else:
            # Quick IP-only check (no suspicious site visits)
            print("\n  [preflight] Quick IP check...")
            await page.goto("https://api.ipify.org?format=json", timeout=15000)
            ip_json = await page.inner_text("body")
            try:
                browser_ip = __import__("json").loads(ip_json.strip()).get("ip", ip_json.strip())
            except Exception:
                browser_ip = ip_json.strip()
            print(f"  Browser IP: {browser_ip}")
            await asyncio.sleep(1)

        # ── Warm up: visit a normal site first so history isn't empty ──
        warmup_sites = [
            "https://www.amazon.com",
            "https://aws.amazon.com",
            "https://docs.aws.amazon.com",
        ]
        warmup = random.choice(warmup_sites)
        print(f"\n  [warmup] Visiting {warmup}...")
        try:
            await page.goto(warmup, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(2, 5))
        except Exception:
            pass

        # ── Step 2: Open AWS & fill email ──
        print("\n[2/7] Opening AWS signup & filling email...")
        await page.goto(SIGNUP_URL, wait_until="networkidle", timeout=300000)
        await page.wait_for_selector("#email-address", timeout=300000)
        await asyncio.sleep(random.uniform(1, 2))

        await human.type_text(page, "#email-address", email)
        await asyncio.sleep(random.uniform(2, 4))
        await human.click(page, '[data-testid="continue-email-button"]')
        print("  Done")

        # ── Step 3: Fill name ──
        print("\n[3/7] Filling name...")
        await page.wait_for_selector(
            '[data-testid="signup-full-name-input"] input', timeout=300000
        )
        await asyncio.sleep(random.uniform(1, 2))

        await human.type_text(
            page, '[data-testid="signup-full-name-input"] input', name
        )
        await asyncio.sleep(random.uniform(2, 4))
        await human.click(page, '[data-testid="signup-next-button"]')
        print("  Done")

        # ── Step 4: Poll OTP ──
        print("\n[4/7] Polling for email OTP...")
        otp = tempmail.poll_otp(email, account_token, email_ts, OTP_POLL_INTERVAL, OTP_MAX_WAIT)
        if not otp:
            email_domain = email.split("@", 1)[1] if "@" in email else ""
            print(f"\n  OTP timeout — blacklisting domain: {email_domain}")
            return {
                "ok": False,
                "error": "otp_timeout",
                "email": email,
                "blacklist_domain": email_domain,
            }
        print(f"  OTP: {otp}")
        otp_domain_value = email.split("@", 1)[1] if "@" in email else ""

        # ── Step 5: Fill OTP ──
        print("\n[5/7] Filling OTP & verifying...")
        await page.wait_for_selector(
            '[data-testid="email-verification-form-code-input"] input',
            timeout=300000,
        )
        await asyncio.sleep(random.uniform(0.5, 1))

        await human.type_text(
            page,
            '[data-testid="email-verification-form-code-input"] input',
            otp,
        )
        await asyncio.sleep(random.uniform(2, 4))
        await human.click(page, '[data-testid="email-verification-verify-button"]')
        print("  Done")

        # ── Step 6: Set password ──
        print("\n[6/7] Setting password...")
        await page.wait_for_selector(
            '[data-testid="test-input"] input', timeout=300000
        )
        await asyncio.sleep(random.uniform(1, 2))

        await human.type_text(page, '[data-testid="test-input"] input', AWS_PASSWORD)
        await asyncio.sleep(random.uniform(0.5, 1))
        await human.type_text(
            page, '[data-testid="test-retype-input"] input', AWS_PASSWORD
        )
        await asyncio.sleep(random.uniform(2, 4))

        # Dismiss cookie consent banner if it's blocking the button
        try:
            banner = page.locator("#awsccc-sb-ux-c")
            if await banner.is_visible(timeout=2000):
                accept_btn = page.locator("#awsccc-cb-btn-accept, [data-id='awsccc-cb-btn-accept']").first
                if await accept_btn.is_visible(timeout=1000):
                    await accept_btn.click()
                else:
                    await page.evaluate("document.getElementById('awsccc-sb-ux-c')?.remove()")
                await asyncio.sleep(0.5)
        except Exception:
            pass

        await human.click(page, '[data-testid="test-primary-button"]')
        print("  Done")

        # ── Step 7: Contact info ──
        print("\n[7/7] Filling contact info...")
        await page.wait_for_selector("button#address\\.country", timeout=300000)
        await asyncio.sleep(random.uniform(1, 2))

        # Country
        await human.select_dropdown(page, "button#address\\.country", "United States")
        await asyncio.sleep(1.5)

        # Address — click "Enter address manually" first to disable autocomplete
        try:
            link = page.get_by_text("Enter address manually", exact=False)
            if await link.is_visible(timeout=3000):
                await link.click()
                await asyncio.sleep(1)
                print("    Switched to manual address entry")
        except Exception:
            pass

        # Address line 1
        addr_sel = 'input[name="address.addressLine1"]'
        await page.locator(addr_sel).click()
        await page.locator(addr_sel).fill("")
        await asyncio.sleep(0.3)
        await human.type_text(page, addr_sel, addr["street"])
        await asyncio.sleep(0.5)

        # Dismiss autocomplete popup if it appeared
        try:
            suggestions = page.locator('[role="listbox"]:visible')
            if await suggestions.count() > 0:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
        except Exception:
            pass

        # City — always clear and fill with correct value
        city_sel = 'input[name="address.city"]'
        await page.locator(city_sel).click()
        await page.locator(city_sel).fill("")
        await asyncio.sleep(0.2)
        await human.type_text(page, city_sel, addr["city"])
        await asyncio.sleep(0.5)

        # State — always force District of Columbia
        state_button = page.locator("button#address\\.state")
        state_input = page.locator('input[name="address.state"]')
        if await state_button.is_visible(timeout=2000):
            await human.select_dropdown(page, "button#address\\.state", "District")
            await asyncio.sleep(0.5)
        elif await state_input.is_visible(timeout=2000):
            await page.locator('input[name="address.state"]').fill("")
            await human.type_text(page, 'input[name="address.state"]', "DC")
            await asyncio.sleep(0.5)

        # Postal — always clear and fill with correct value
        postal_sel = 'input[name="address.postalCode"]'
        await page.locator(postal_sel).click()
        await page.locator(postal_sel).fill("")
        await asyncio.sleep(0.2)
        await human.type_text(page, postal_sel, addr["postal"])
        await asyncio.sleep(0.5)

        # Phone code — default is already +1 (US) after selecting country,
        # only change if it's wrong
        try:
            phone_btn = page.locator("button#address\\.phoneCode")
            phone_btn_text = (await phone_btn.inner_text()).strip()
            if "+1" not in phone_btn_text:
                print(f"    Phone code wrong ({phone_btn_text}) — selecting US +1")
                await human.select_dropdown(page, "button#address\\.phoneCode", "United States")
                await asyncio.sleep(1)
            else:
                print(f"    Phone code already correct: {phone_btn_text}")
        except Exception:
            pass

        # Phone number
        await human.type_text(page, 'input[name="address.phoneNumber"]', phone)
        await asyncio.sleep(random.uniform(1, 2))

        # ── Final check: verify all fields before submit ──
        async def get_val(sel: str) -> str:
            try:
                return (await page.locator(sel).input_value()).strip()
            except Exception:
                return ""

        checks = {
            "Address": (
                'input[name="address.addressLine1"]',
                await get_val('input[name="address.addressLine1"]'),
                addr["street"],
            ),
            "City": (
                'input[name="address.city"]',
                await get_val('input[name="address.city"]'),
                addr["city"],
            ),
            "Postal": (
                'input[name="address.postalCode"]',
                await get_val('input[name="address.postalCode"]'),
                addr["postal"],
            ),
            "Phone": (
                'input[name="address.phoneNumber"]',
                await get_val('input[name="address.phoneNumber"]'),
                phone,
            ),
        }

        all_ok = True
        for label, (sel, cur, expected) in checks.items():
            if not cur:
                print(f"    [FIX] {label} empty — filling: {expected}")
                await page.locator(sel).fill("")
                await human.type_text(page, sel, expected)
                await asyncio.sleep(0.3)
                all_ok = False
            elif cur != expected:
                print(f"    [FIX] {label} wrong ({cur}) — correcting to: {expected}")
                await page.locator(sel).fill("")
                await human.type_text(page, sel, expected)
                await asyncio.sleep(0.3)
                all_ok = False
            else:
                print(f"    [OK]  {label}: {cur}")

        # State check (dropdown, not input)
        state_btn = page.locator("button#address\\.state")
        if await state_btn.is_visible(timeout=2000):
            state_text = (await state_btn.inner_text()).strip()
            if "district" in state_text.lower() or "dc" in state_text.lower():
                print(f"    [OK]  State: {state_text}")
            else:
                print(f"    [FIX] State wrong ({state_text}) — selecting District of Columbia")
                await human.select_dropdown(page, "button#address\\.state", "District")
                await asyncio.sleep(0.5)
                all_ok = False

        if all_ok:
            print("    All fields verified OK")
        await asyncio.sleep(random.uniform(1, 2))

        # Submit
        await human.click(
            page, '[data-testid="starter-home-contact-info-submit-button"]'
        )
        print("  Done")

        # ── Detect payment wall ──
        try:
            await page.wait_for_selector(
                '[data-testid="payment-widget-page"], [data-testid="aws-payment-profiles-widget-root"]',
                timeout=15000,
            )
            print("\n  [!] Payment page detected — account requires credit card.")
            print("      Closing browser, moving to next proxy.")
            return {
                "ok": False,
                "error": "payment_required",
                "email": email,
                "otp_domain": otp_domain_value,
            }
        except Exception:
            pass  # No payment page — signup completed normally

        # ── Finish OTPMurah ──
        if sewa and otpmurah_key:
            try:
                import otpmurah
                otpmurah.finish(otpmurah_key, sewa["id"])
                print(f"  OTPMurah activation finished")
            except Exception:
                pass

        email_domain = email.split("@", 1)[1] if "@" in email else ""
        result = {
            "ok": True,
            "email": email,
            "password": AWS_PASSWORD,
            "name": name,
            "proxy_ip": proxy_ip,
            "otp_domain": email_domain,
        }

        print(f"\n{'='*60}")
        print(f"  SIGNUP COMPLETE!")
        print(f"  Email:    {email}")
        print(f"  Password: {AWS_PASSWORD}")
        print(f"  Name:     {name}")
        print(f"  Proxy IP: {proxy_ip}")
        print(f"{'='*60}")

        # Keep browser open — tunggu manual close atau Ctrl+C
        print("\nBrowser tetap terbuka. Tutup manual untuk lanjut ke account berikutnya.")
        try:
            await page.wait_for_timeout(999_999_999)
        except Exception:
            pass

        return result

    except Exception as exc:
        # Cancel OTPMurah on failure
        if sewa and otpmurah_key:
            try:
                import otpmurah
                otpmurah.cancel(otpmurah_key, sewa["id"])
                print(f"  OTPMurah activation cancelled (refund)")
            except Exception:
                pass

        print(f"\n  ERROR: {exc}")
        return {
            "ok": False,
            "error": str(exc),
            "email": email,
            "otp_domain": otp_domain_value,
        }

    finally:
        await bro.close()
        browser._wipe_session(
            os.path.join(tempfile.gettempdir(), f"patchright_profile_{proxy_port or 'direct'}")
        )
