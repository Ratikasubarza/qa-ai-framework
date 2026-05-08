# Mobile Testing Setup — Android (Appium)

## Prerequisites

### 1. Install Node.js + Appium
```bash
brew install node
npm install -g appium
appium --version  # should be 2.x
```

### 2. Install Appium UiAutomator2 Driver
```bash
appium driver install uiautomator2
appium driver list --installed
```

### 3. Install Android SDK
```bash
brew install --cask android-studio
# After install, open Android Studio → SDK Manager
# Install: Android SDK Platform 33 (Android 13)
# Install: Android SDK Build-Tools 33.0.0
# Install: Android Emulator
```

Set environment variables in ~/.zshrc:
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
```

### 4. Create Android Emulator
```bash
# Via Android Studio: Tools → Device Manager → Create Device
# Or command line:
avdmanager create avd -n hono_test -k "system-images;android-33;google_apis;arm64-v8a"
```

### 5. Install Python dependencies
```bash
pip install Appium-Python-Client selenium
```

---

## Running Tests

### Start Appium server (Terminal 1):
```bash
appium --port 4723
```

### Start emulator (Terminal 2):
```bash
emulator -avd hono_test
# Wait for emulator to fully boot
adb devices  # should show emulator-5554
```

### Update .env with app config:
```
ANDROID_APP_PACKAGE=com.hono.app
ANDROID_APP_ACTIVITY=com.hono.app.MainActivity
ANDROID_DEVICE_NAME=emulator-5554
ANDROID_APK_PATH=/path/to/hono.apk  # optional if app already installed
```

### Find app package and activity from APK:
```bash
# If you have the APK:
aapt dump badging /path/to/hono.apk | grep -E "package|launchable"

# Or from installed app on device:
adb shell pm list packages | grep hono
adb shell dumpsys package com.hono.app | grep "Activity"
```

### Run tests:
```bash
PYTHONPATH=. pytest features/login/steps/login_android_test.py -v -s
```

---

## Resource IDs

Resource IDs depend on the actual app implementation.
To find them:

### Option 1: Appium Inspector
```bash
appium-inspector  # GUI tool to inspect elements
```

### Option 2: UIAutomatorViewer
```bash
# While app is running on device:
$ANDROID_HOME/tools/bin/uiautomatorviewer
```

### Option 3: Script
```python
from platforms.mobile.appium_driver import AppiumDriver
driver = AppiumDriver(app_package="com.hono.app", app_activity="...")
d = driver.start()
print(d.page_source)  # Full XML of current screen
```

### Update login_android_test.py with actual IDs:
```python
EMAIL_FIELD    = "actual_email_resource_id"
PASSWORD_FIELD = "actual_password_resource_id"
LOGIN_BUTTON   = "actual_login_button_id"
ERROR_MESSAGE  = "actual_error_message_id"
FEED_SCREEN    = "actual_feed_container_id"
```

---

## Common Issues

| Error | Fix |
|-------|-----|
| `Connection refused :4723` | Start Appium: `appium --port 4723` |
| `No device found` | Check `adb devices` — start emulator |
| `App not installed` | Set `ANDROID_APK_PATH` in .env |
| `Element not found` | Update resource IDs in test file |
| `UiAutomator2 not found` | `appium driver install uiautomator2` |
