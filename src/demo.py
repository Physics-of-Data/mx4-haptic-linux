#!/usr/bin/env python3
"""Cycle through all 16 MX Master 4 haptic waveforms with a 3-second gap.

Optional --level N (0-100) sets the global haptic-level for the run and
restores whatever was set beforehand on exit (including Ctrl+C).

Uses solaar, same as watch.py. solaar on Python 3.14 crashes on exit after
firing the haptic/write (Gio marshal TypeError); the command still lands,
so we suppress solaar's stderr and ignore its exit code here.
"""

import argparse
import logging
import re
import subprocess
import time

DEVICE_NAME = "MX Master 4"

WAVEFORMS = [
    "SHARP STATE CHANGE",
    "DAMP STATE CHANGE",
    "SHARP COLLISION",
    "DAMP COLLISION",
    "SUBTLE COLLISION",
    "HAPPY ALERT",
    "ANGRY ALERT",
    "COMPLETED",
    "SQUARE",
    "WAVE",
    "FIREWORK",
    "MAD",
    "KNOCK",
    "JINGLE",
    "RINGING",
    "WHISPER COLLISION",
]


def play(pattern: str) -> None:
    subprocess.run(
        ["solaar", "config", DEVICE_NAME, "haptic-play", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )


def read_level() -> int | None:
    """Return current haptic-level, or None if it can't be read."""
    try:
        result = subprocess.run(
            ["solaar", "config", DEVICE_NAME],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return None
    match = re.search(r"^haptic-level\s*=\s*(\d+)", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def set_level(level: int) -> None:
    subprocess.run(
        ["solaar", "config", DEVICE_NAME, "haptic-level", str(level)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )


def level_arg(value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be an integer, got {value!r}")
    if not 0 <= n <= 100:
        raise argparse.ArgumentTypeError(f"must be between 0 and 100, got {n}")
    return n


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cycle all 16 MX Master 4 haptic waveforms.",
    )
    parser.add_argument(
        "--level",
        type=level_arg,
        metavar="N",
        help="Haptic intensity 0-100 for the cycle (restored on exit). "
             "If omitted, the current device setting is used unchanged.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    original_level: int | None = None
    if args.level is not None:
        original_level = read_level()
        if original_level is None:
            logging.warning("Could not read current haptic-level; it won't be restored on exit")
        else:
            logging.info(f"haptic-level: {original_level} -> {args.level} (will restore on exit)")
        set_level(args.level)

    try:
        logging.info(f"Cycling {len(WAVEFORMS)} waveforms with a 3s gap each")
        for i, pattern in enumerate(WAVEFORMS, 1):
            logging.info(f"[{i:2}/{len(WAVEFORMS)}] {pattern}")
            play(pattern)
            if i < len(WAVEFORMS):
                time.sleep(3)
    finally:
        if original_level is not None:
            logging.info(f"Restoring haptic-level to {original_level}")
            set_level(original_level)


if __name__ == "__main__":
    main()
