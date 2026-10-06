"""
AutoSecOps GreenSentinel - Automated High-Resolution Screenshot Capture
Captures 6 publication-ready screenshots from http://localhost:8080 into assets/screenshots/
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "assets" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:8080"


def capture_all_screenshots():
    print(f"[*] Starting screenshot capture pipeline against {URL}...")
    
    with sync_playwright() as p:
        # Launch browser with high resolution viewport (1920x1080)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,  # 2x Retina rendering for crisp text/charts
        )
        page = context.new_page()
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)  # allow animations, fonts, and telemetry data to load

        # -------------------------------------------------------------
        # 1. 01_hero_dashboard.png - Full Grandma Theory Hero View
        # -------------------------------------------------------------
        hero_path = SCREENSHOT_DIR / "01_hero_dashboard.png"
        page.screenshot(path=str(hero_path), full_page=False)
        print(f"[+] Saved 1/6: {hero_path.name}")

        # -------------------------------------------------------------
        # 2. 02_auto_healed_diff.png - Interactive Unified Git Diff Modal
        # -------------------------------------------------------------
        # Click stage card 3 (verify) or trigger openDiffModal()
        page.evaluate("openDiffModal()")
        time.sleep(1)
        diff_modal_path = SCREENSHOT_DIR / "02_auto_healed_diff.png"
        page.screenshot(path=str(diff_modal_path), full_page=False)
        print(f"[+] Saved 2/6: {diff_modal_path.name}")
        page.evaluate("closeDiffModal()")
        time.sleep(0.5)

        # -------------------------------------------------------------
        # 3. 03_carbon_router.png - Smart Low-Carbon Grid Selector
        # -------------------------------------------------------------
        # Select europe-west9 and scroll to the grid router card
        page.evaluate("document.getElementById('region-selector').value = 'europe-west9'; updateRegionImpact('europe-west9');")
        router_element = page.locator(".grid.grid-cols-1.lg\\:grid-cols-2.gap-8")
        router_path = SCREENSHOT_DIR / "03_carbon_router.png"
        if router_element.count() > 0:
            router_element.first.screenshot(path=str(router_path))
        else:
            page.screenshot(path=str(router_path), full_page=False)
        print(f"[+] Saved 3/6: {router_path.name}")

        # -------------------------------------------------------------
        # 4. 04_devsecops_stages.png - Clean Crop of All 9 Lifecycle Stages
        # -------------------------------------------------------------
        stages_section = page.locator("section:has(#stages-grid)")
        stages_path = SCREENSHOT_DIR / "04_devsecops_stages.png"
        if stages_section.count() > 0:
            stages_section.first.screenshot(path=str(stages_path))
        else:
            page.screenshot(path=str(stages_path), full_page=False)
        print(f"[+] Saved 4/6: {stages_path.name}")

        # -------------------------------------------------------------
        # 5. 05_sci_telemetry.png - Hardware Telemetry and GSF SCI Card
        # -------------------------------------------------------------
        telemetry_section = page.locator(".grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4.gap-5")
        sci_path = SCREENSHOT_DIR / "05_sci_telemetry.png"
        if telemetry_section.count() > 0:
            telemetry_section.first.screenshot(path=str(sci_path))
        else:
            page.screenshot(path=str(sci_path), full_page=False)
        print(f"[+] Saved 5/6: {sci_path.name}")

        # -------------------------------------------------------------
        # 6. 06_circuit_breaker.png - Agent Log Card with Circuit Breaker
        # -------------------------------------------------------------
        agent_log_card = page.locator("#agent-console").locator("xpath=..")
        circuit_path = SCREENSHOT_DIR / "06_circuit_breaker.png"
        if agent_log_card.count() > 0:
            agent_log_card.first.screenshot(path=str(circuit_path))
        else:
            page.screenshot(path=str(circuit_path), full_page=False)
        print(f"[+] Saved 6/6: {circuit_path.name}")

        browser.close()
        print(f"[OK] All 6 screenshots saved successfully to: {SCREENSHOT_DIR}")


if __name__ == "__main__":
    capture_all_screenshots()
