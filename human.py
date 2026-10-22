"""Human-like browser interactions: type, click, dropdown, mouse."""

import asyncio
import random


async def _move_mouse_to(page, x: float, y: float, steps: int = 0):
    """Move mouse with natural curve (bezier-like jitter)."""
    if steps == 0:
        steps = random.randint(5, 15)
    current = await page.evaluate("() => ({x: 0, y: 0})")
    for i in range(1, steps + 1):
        t = i / steps
        jx = random.uniform(-3, 3)
        jy = random.uniform(-3, 3)
        nx = current["x"] + (x - current["x"]) * t + jx
        ny = current["y"] + (y - current["y"]) * t + jy
        await page.mouse.move(nx, ny)
        await asyncio.sleep(random.uniform(0.005, 0.02))


async def type_text(page, selector: str, text: str, delay=(40, 120)):
    """Type character by character with variable human-like delays."""
    el = page.locator(selector)
    await el.click()
    await el.fill("")
    for ch in text:
        d = random.randint(*delay)
        if ch == " ":
            d = random.randint(30, 80)
        elif random.random() < 0.05:
            d = random.randint(200, 400)
        await el.press_sequentially(ch, delay=d)
    await asyncio.sleep(random.uniform(0.2, 0.6))


async def click(page, selector: str, wait_after=(0.5, 1.5)):
    """Click with mouse movement and random delay after."""
    el = page.locator(selector)
    await el.scroll_into_view_if_needed()
    await asyncio.sleep(random.uniform(0.1, 0.3))

    box = await el.bounding_box()
    if box:
        tx = box["x"] + box["width"] * random.uniform(0.2, 0.8)
        ty = box["y"] + box["height"] * random.uniform(0.2, 0.8)
        await _move_mouse_to(page, tx, ty)

    await el.click()
    await asyncio.sleep(random.uniform(*wait_after))


async def select_dropdown(page, btn_selector: str, filter_text: str):
    """Open a Cloudscape dropdown, type filter, click matching option."""
    btn = page.locator(btn_selector)
    await btn.scroll_into_view_if_needed()
    await btn.click()
    await asyncio.sleep(random.uniform(0.6, 1.0))

    # Tunggu sampai benar-benar expanded — Cloudscape animasi bisa lambat
    for _ in range(5):
        expanded = await btn.get_attribute("aria-expanded")
        if expanded == "true":
            break
        await btn.click()
        await asyncio.sleep(0.6)

    # Tunggu filter input visible — coba beberapa selector Cloudscape
    filter_input = None
    for sel in [
        '[role="dialog"][data-open="true"] input',
        '[role="dialog"]:visible input',
        'input[role="combobox"]:visible',
        'input[placeholder*="Filter"]:visible',
    ]:
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="visible", timeout=3000)
            filter_input = loc
            break
        except Exception:
            continue

    if filter_input is None:
        # Fallback: ArrowDown + Enter tanpa filter
        await btn.press("ArrowDown")
        await asyncio.sleep(0.3)
        await btn.press("Enter")
        return

    await filter_input.fill("")
    await filter_input.press_sequentially(
        filter_text, delay=random.randint(30, 60)
    )
    await asyncio.sleep(1.2)  # tunggu list filter render

    option = page.locator(
        f'[role="option"]:visible:has-text("{filter_text}")'
    ).first
    try:
        await option.click(timeout=5000)
    except Exception:
        await filter_input.press("ArrowDown")
        await asyncio.sleep(0.2)
        await filter_input.press("Enter")

    await asyncio.sleep(0.5)
