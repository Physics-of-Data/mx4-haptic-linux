# CLAUDE.md

Trigger MX Master 4 haptics on Linux desktop notifications. Two small Python scripts, a Makefile, an XDG autostart entry. That's the whole repo.

## Runtime

- [src/watch.py](src/watch.py) — the daemon. Spawns `dbus-monitor` as a subprocess, parses its text output line-by-line, and for each `Notify` call: short-circuits silently if the app (lowercased) is in `MUTED_APPS`, otherwise resolves a haptic pattern via `APP_PATTERNS` → `URGENCY_PATTERNS` → `HAPTIC_PATTERN`. Plays it by shelling out to `solaar config "MX Master 4" haptic-play <PATTERN>`.
- [src/demo.py](src/demo.py) — cycles all 16 waveforms with a 3s gap. `--level N` (0–100) sets `haptic-level` for the run and restores the previous value in a `try/finally` on exit.

Both scripts are **stdlib-only**. No PyPI dependencies. They do need `solaar` and `dbus-monitor` on `PATH`.

## Why this approach works

A few non-obvious calls that are load-bearing:

1. **Everything goes through `solaar`, not HID++ directly.** An earlier iteration (in the retired `mx4notifications` repo) implemented HID++ 2.0 itself via libhidapi. It broke against a Bolt receiver because the receiver requires a *slot index* (1–6) as the HID++ `device_idx`, not the USB `interface_number` that naive `hid.enumerate` returns. `solaar` already handles receiver enumeration and slot discovery, so we let it.
2. **`dbus-monitor` subprocess, not `dbus-python`.** Parsing `dbus-monitor`'s text stream keeps the project stdlib-only and removes a pile of D-Bus binding / GLib dependencies. The parse is forgiving (see [watch.py:86-113](src/watch.py#L86-L113)) — it looks for `member=Notify`, then the first `string` line, then any `byte` line containing `urgency`.
3. **App-name dispatch, not just urgency.** The first `string` arg of the `Notify` D-Bus call is the app name. We route on that before falling back to urgency. This is what makes the per-app table meaningful — Claude Code → `COMPLETED`, Firefox → `KNOCK`, etc.
4. **Tolerating solaar-on-Python-3.14.** `solaar config` currently crashes on shutdown with `TypeError: Unable to marshal str as an array` (inside `Gio.Application.run`). The HID++ write always lands *before* the crash. `demo.py` suppresses solaar's stderr and ignores its exit code for a clean log; `watch.py` leaves the warning visible (notifications are sparse and it's useful signal if solaar ever genuinely fails).

## Install / deploy model

The Makefile owns a `MANAGED` list of `repo-path|install-path` pairs. Three targets act on it symmetrically:

- `make autostart` — copy repo → installed (scripts get `755`, the desktop file gets `644`)
- `make fetch` — copy installed → repo (for capturing out-of-band edits to `~/.local/bin/*` or `~/.config/autostart/mx4-haptics.desktop`)
- `make status` — `[OK]` / `[DIFF]` / `[MISSING]` per pair; on `[DIFF]`, reports which side is newer by mtime

If you add a new deployed artifact, add one line to `MANAGED` and all three targets pick it up.

### `__HOME__` placeholder substitution (`*.desktop` only)

The repo's `autostart/mx4-haptics.desktop` contains `Exec=__HOME__/.local/bin/mx4-watch`. The literal string `__HOME__` is a placeholder — not a shell variable, not an env var, just a sentinel chosen because it's vanishingly unlikely to appear in real text. All three Makefile targets handle it via `sed`:

- **`make autostart`** — for any `*.desktop` source, `sed "s|__HOME__|$HOME|g"` rewrites the file into a tempfile, then `install` copies that tempfile to the target. The deployed file ends up with the absolute path baked in (`Exec=/home/msfz751/.local/bin/mx4-watch`). The repo file is never touched.
- **`make fetch`** — reverse direction: `sed "s|$HOME|__HOME__|g"` rewrites the *installed* file into a tempfile, then compares/copies that to the repo source. So if you hand-edit `~/.config/autostart/mx4-haptics.desktop` to change a key, `make fetch` brings the change back into the repo with `$HOME` re-templated.
- **`make status`** — same reverse substitution into a tempfile, then `cmp` against the repo source. This is what makes `[OK]` honest: a freshly-deployed file reports `[OK]` even though the on-disk bytes differ.

Why a placeholder instead of shell expansion in `Exec=` itself: see the convention bullet below. KDE Plasma 6's autostart layer can't reliably evaluate `$HOME`, so substitution has to happen *before* the file reaches that layer.

To extend the mechanism (e.g. another templated `*.desktop` file, or a new placeholder), the dispatch happens in the `case "$src" in *.desktop)` arm of each target — keep the same sed pattern in both directions so the round-trip stays lossless.

## Conventions to preserve

- **Stdlib-only.** If a change starts pulling in `dbus-python`, `hid`, `pygobject`, reconsider — we intentionally moved away from all of those.
- **`DEVICE_NAME = "MX Master 4"` is duplicated** in `watch.py` and `demo.py` on purpose. When deployed as `~/.local/bin/mx4-watch` and `~/.local/bin/mx4-demo`, they don't share a module — keep them self-contained.
- **`haptic-level` is global device state.** Anything that changes it for the duration of a run must restore it in a `finally` block (see `demo.py`).
- **The `.desktop` `Exec=` uses an absolute path with a `__HOME__` placeholder** that the Makefile substitutes at install time (and reverses on `fetch`/`status`). Do not use `~`, `$HOME`, or `sh -c` indirection in the repo's `Exec=` line. We tried both: `~` is unsupported by the spec, and `sh -c "exec \"\$HOME/..\""` parses correctly under `desktop-file-validate` and `gio launch` but breaks under KDE Plasma 6, which routes autostart through `systemd-xdg-autostart-generator`. The generator emits "Ignoring unknown escape sequences" for `\$` and produces a unit whose `sh -c` payload still contains a literal `$HOME`, so `mx4-watch` never starts. The templated absolute path sidesteps all three layers.
- **After editing the desktop file, validate AND test through the real path.** `desktop-file-validate` and `gio launch …/autostart/mx4-haptics.desktop` are necessary but not sufficient — KDE 6 uses neither at session start. Confirm with `systemctl --user daemon-reload && systemctl --user start 'app-mx4\x2dhaptics@autostart.service'` and check `journalctl --user -b | grep mx4`. `Restart=always` is a *systemd* key, not a desktop-entry key — it fails validation and does nothing useful here.

## Not in scope

- A direct-HID fallback for when `solaar` isn't installed. We tried; receiver-slot discovery is the hard part and solaar solves it for us.
- Per-haptic intensity. HID++ 0x0B4E does not expose a per-call intensity; only the global `haptic-level`.
- Parsing notification bodies to distinguish web-app notifications (e.g. Gmail in Firefox). The D-Bus app name is always the browser's.
