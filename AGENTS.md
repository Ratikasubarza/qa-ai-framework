# AGENTS.md — QA AI Framework
> Last updated: May 2026 | Owner: Ratikasubarza | Senior QE → AI Engineering

---

## ⚠️ Critical Rules — Read First

1. **NEVER break existing passing tests** — always run affected test suite after changes
2. **NEVER hardcode credentials** — use TestConfig or test data classes
3. **NEVER use system Python** — always use `./venv/bin/python3.11`
4. **NEVER change folder structure** without updating all imports
5. **ALWAYS commit after milestone** — git add → commit → push

---

## Project Overview

AI-powered QA automation framework for **Hono app** (app-dev.thehono.com).
Combines LLM agents (OpenRouter) + Playwright + Appium + LangGraph orchestration.

**Target app:** `app.thehono.development` (Flutter Android)
**API:** `https://api-dev.thehono.com`
**Web:** `https://app-dev.thehono.com`
**DB:** MySQL `hono_dev` (staging, requires VPN)

---

## Folder Structure
/Users/ratikasubarza/Documents/Ratika/automation-agents/qa-ai-framework-backup-20260508/venv/bin/python3.11 << 'EOF'
from platforms.mobile.appium_driver import AppiumDriver
from config.test_config import TestConfig
from appium.webdriver.common.appiumby import AppiumBy
import re, time, subprocess

ADB = "~/Downloads/platform-tools/adb"

driver = AppiumDriver(
    app_package=TestConfig.ANDROID_PACKAGE,
    app_activity=TestConfig.ANDROID_ACTIVITY,
    device_name=TestConfig.ANDROID_DEVICE,
    platform_version=TestConfig.ANDROID_VERSION,
)
driver.start()
time.sleep(5)

def get_elements(label):
    for attempt in range(5):
        try:
            time.sleep(3)
            source = driver.driver.page_source
            cds = re.findall(r'content-desc="([^"]+)"', source)
            print(f"\n=== {label} ===")
            for cd in cds[:25]:
                if cd and not cd.startswith('&#'):
                    print(f"  '{cd}'")
            return source
        except:
            time.sleep(3)
    return ""

def safe_fill(index, text):
    for attempt in range(3):
        try:
            els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
            if len(els) > index:
                els[index].click(); time.sleep(0.5)
                els[index].send_keys(text); time.sleep(0.3)
                print(f"  ✓ [{index}] = {text}"); return True
        except: time.sleep(2)
    return False

def tap_continue():
    for attempt in range(3):
        try:
            driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
            time.sleep(6); print("  ✓ Continue"); return True
        except: time.sleep(3)
    return False

def adb_tap(x, y):
    subprocess.run(f'{ADB} shell input tap {x} {y}', shell=True)
    time.sleep(1)

# Steps 2+3
safe_fill(0, "Test Onboard User")
driver.hide_keyboard(); time.sleep(1); tap_continue()
safe_fill(0, "QA Engineer"); time.sleep(0.5)
safe_fill(1, "Hono Testing Inc")
driver.hide_keyboard(); time.sleep(1); tap_continue()

# Country
els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
adb_tap(els[0].location['x'] + els[0].size['width']//2,
        els[0].location['y'] + els[0].size['height']//2)
time.sleep(3)
search_els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
search_els[0].click(); time.sleep(0.5)
search_els[0].send_keys("Indonesia"); time.sleep(2)
driver.find(AppiumBy.ACCESSIBILITY_ID, "Indonesia", timeout=5).click()
time.sleep(4)

# City
adb_tap(360, 700); time.sleep(3)
els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
els[0].click(); time.sleep(0.5)
els[0].send_keys("Jakarta"); time.sleep(3)
driver.find(AppiumBy.ACCESSIBILITY_ID, "Jakarta Pusat", timeout=3).click()
time.sleep(3)
tap_continue()
print("✓ Steps 2-4 done")

# Step 5 - Industries
get_elements("Industries screen")

# Try tap Continue to see what options are available or tap the dropdown
try:
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=3)
    print("Continue exists — tap to open industries?")
except:
    pass

# Tap screen center to open dropdown
adb_tap(360, 400)
time.sleep(3)
get_elements("After tap industries area")

driver.stop()
