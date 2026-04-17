#!/usr/bin/env python3
"""
MX Master 4 Notification Haptics
Listens for KDE/freedesktop D-Bus notifications and triggers haptic feedback
on the MX Master 4 via solaar config.
"""

import logging
import subprocess
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

DEVICE_NAME = "MX Master 4"

# Choose your preferred haptic pattern:
# Strong/distinct: SHARP STATE CHANGE, DAMP STATE CHANGE, SHARP COLLISION,
#                  DAMP COLLISION, SUBTLE COLLISION, HAPPY ALERT, ANGRY ALERT, COMPLETED
# Soft/subtle:     SQUARE, WAVE, FIREWORK, MAD, KNOCK, JINGLE, RINGING, WHISPER COLLISION
HAPTIC_PATTERN = "HAPPY ALERT"

# Map application names (lowercase) to specific haptic patterns
APP_PATTERNS = {
    "claude code": "COMPLETED",
    "firefox": "KNOCK",
    "obsidian": "WAVE",
    "dolphin": "SUBTLE COLLISION",
    "rsnapshot": "JINGLE",
}

# Apps whose notifications should never trigger a haptic (lowercase).
MUTED_APPS = {
    "spectacle",
}

# Optional: map notification urgency levels to different patterns
# urgency: 0=low, 1=normal, 2=critical
URGENCY_PATTERNS = {
    0: "SUBTLE COLLISION",   # low urgency - subtle
    1: "HAPPY ALERT",        # normal - standard
    2: "ANGRY ALERT",        # critical - strong
}


def trigger_haptic(pattern: str = HAPTIC_PATTERN) -> bool:
    """Trigger haptic feedback on MX Master 4 via solaar config."""
    try:
        result = subprocess.run(
            ["solaar", "config", DEVICE_NAME, "haptic-play", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logging.debug(f"Haptic triggered: {pattern}")
            return True
        else:
            logging.warning(f"Haptic failed: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        logging.warning("Haptic command timed out")
        return False
    except FileNotFoundError:
        logging.error("solaar not found - is it installed?")
        return False


def watch_notifications():
    """Monitor D-Bus for desktop notifications and trigger haptics."""
    import subprocess as sp

    logging.info(f"MX Master 4 notification haptics started")
    logging.info(f"Default pattern: {HAPTIC_PATTERN}")
    logging.info("Listening for notifications... Press Ctrl+C to stop")
    logging.info("Test with: notify-send 'Test' 'Message'")

    proc = sp.Popen(
        ["dbus-monitor", "--session", "interface='org.freedesktop.Notifications'"],
        stdout=sp.PIPE,
        stderr=sp.DEVNULL,
        text=True,
    )

    logging.info("Starting dbus-monitor...")

    urgency = 1  # default urgency
    in_notify_call = False

    try:
        for line in proc.stdout:
            line = line.strip()

            # Detect a Notify method call (new notification)
            if "member=Notify" in line:
                in_notify_call = True
                urgency = 1  # reset to normal

            # Look for urgency hint within the notification
            if in_notify_call and "urgency" in line.lower():
                try:
                    # urgency value follows on next lines - rough parse
                    if "byte" in line:
                        urgency = int(line.split()[-1])
                except (ValueError, IndexError):
                    urgency = 1

            # Trigger on the app name string (first string arg of Notify)
            if in_notify_call and line.startswith("string"):
                # Extract app name: dbus-monitor outputs 'string "AppName"'
                app_name = line.split('"', 1)[1].rstrip('"') if '"' in line else ""
                logging.debug(f"Raw app name: '{app_name}' (lowered: '{app_name.lower()}')")
                key = app_name.lower()
                if key in MUTED_APPS:
                    logging.info(f"✗ [{app_name}] muted")
                    in_notify_call = False
                    continue
                pattern = APP_PATTERNS.get(key) \
                       or URGENCY_PATTERNS.get(urgency) \
                       or HAPTIC_PATTERN
                logging.info(f"✓ [{app_name}] triggering haptic: {pattern}")
                trigger_haptic(pattern)
                in_notify_call = False

    except KeyboardInterrupt:
        logging.info("Stopping...")
    finally:
        proc.terminate()


if __name__ == "__main__":
    # Quick test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        pattern = sys.argv[2] if len(sys.argv) > 2 else HAPTIC_PATTERN
        logging.info(f"Testing haptic pattern: {pattern}")
        success = trigger_haptic(pattern)
        sys.exit(0 if success else 1)

    watch_notifications()
