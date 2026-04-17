# mx4-haptic-linux

Trigger Logitech MX Master 4 haptic feedback when Linux desktop notifications arrive.

`watch.py` listens to the D-Bus notification stream and, for each incoming notification, picks a haptic waveform (by app name, urgency, or a default) and asks `solaar` to play it on the mouse.

> **Connection:** both `watch.py` and `demo.py` go through `solaar`, so they work with any transport — Bolt receiver, Unifying receiver, direct Bluetooth, or USB cable. If `solaar` sees the mouse, these scripts do too.

## Requirements

- Linux with a D-Bus session bus (KDE, GNOME, XFCE, Hyprland, …)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (for env/version management)
- [solaar](https://pwr-solaar.github.io/Solaar/) with the MX Master 4 paired — any transport works (Bolt receiver, Unifying receiver, direct Bluetooth, or USB cable); the watcher goes through `solaar`, so whatever solaar sees, this works with
- `dbus-monitor` (ships with D-Bus)

## Install

```sh
make deps       # create .venv via uv (no runtime PyPI deps today)
make autostart  # install scripts to ~/.local/bin and the XDG autostart entry
```

After `make autostart`, the next login starts `mx4-watch` automatically.
To start it now without logging out:

```sh
~/.local/bin/mx4-watch &
```

## Usage

| Command | What it does |
|---|---|
| `make run-watch` | Run the notification watcher from the repo (foreground) |
| `make run-demo` | Cycle all 16 haptic waveforms with a 3 s gap |
| `make run-demo LEVEL=100` | Same, but set intensity (0–100) for the run and restore it on exit |
| `make status` | Report `[OK]` / `[DIFF]` / `[MISSING]` for each managed file |
| `make autostart` | (Re)install scripts + autostart entry |
| `make fetch` | Copy installed files back over `src/*` and `autostart/*` |

## Configuration

Edit [src/watch.py](src/watch.py):

- `APP_PATTERNS` — map D-Bus app name (lowercase) to a waveform
- `URGENCY_PATTERNS` — map urgency (0/1/2) to a waveform
- `HAPTIC_PATTERN` — default when nothing else matches

Priority: app → urgency → default.

Browser-delivered web-app notifications (e.g. Gmail in Firefox) arrive with the browser's app name, not the web app's. There's no reliable way to distinguish them without parsing the notification body.

## Haptic intensity

Intensity is a global device setting; waveforms have their own baked-in feel on top of it.

```sh
solaar config "MX Master 4" haptic-level 100   # max
solaar config "MX Master 4" haptic-level 0     # off
solaar config "MX Master 4"                    # read current value
```

## Managed file layout

`make status` / `autostart` / `fetch` operate on these pairs:

| Repo source | Installed target |
|---|---|
| `src/watch.py` | `~/.local/bin/mx4-watch` |
| `src/demo.py` | `~/.local/bin/mx4-demo` |
| `autostart/mx4-haptics.desktop` | `~/.config/autostart/mx4-haptics.desktop` |

## Notes

- On Python 3.14, `solaar config` prints a `Gio marshal` traceback after every command. The haptic / setting write has already landed by then — the demo script suppresses solaar's stderr for a clean log; `watch.py` leaves it visible.
