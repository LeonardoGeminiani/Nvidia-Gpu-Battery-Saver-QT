# GPU Battery Saver


A minimal GUI app to switch GPU modes on Optimus laptops (Intel + Nvidia) using [envycontrol](https://github.com/bayasdev/envycontrol).

Tested on: Intel i9 13th gen (Iris Xe) + Nvidia RTX 5060, Fedora Linux.

---

## System requirements

- Python 3.10+
- `envycontrol` installed and on PATH
- `pkexec` (part of polkit — standard on Fedora/Ubuntu/Arch)

Install envycontrol:
```bash
pip install envycontrol
```

---

## Option 1 — Run from source (development)

Sets up a local `.venv` so nothing touches your system Python.

```bash
bash setup.sh
.venv/bin/python gui.py
```

> **Note:** always use `.venv/bin/python`, not `python` or `python3`. The system Python does not have the dependencies installed — only the venv does.

---

## Option 2 — Install to system

Copies the app to `/usr/local/lib/gpubatterysaver/`, creates a local venv there with all deps, adds a launcher to `/usr/local/bin/`, and registers the `.desktop` entry.

```bash
sudo bash install.sh
```

Then run from anywhere:
```bash
gpubatterysaver
```

Or launch it from your application menu.

To remove:
```bash
sudo bash uninstall.sh
```

Both scripts accept `--prefix` to change the install root:
```bash
sudo bash install.sh --prefix /usr
sudo bash uninstall.sh --prefix /usr
```

---

## Option 3 — Build an AppImage

Requires `appimagetool` on your PATH (download from the AppImageKit GitHub releases page).

```bash
bash build.sh
```

This will:
1. Create a local `.venv` and install deps
2. Bundle the app with PyInstaller
3. Assemble an AppDir
4. Produce `GpuBatterySaver-x86_64.AppImage`

Run it:
```bash
chmod +x GpuBatterySaver-x86_64.AppImage
./GpuBatterySaver-x86_64.AppImage
```

---

## Headless / scripting usage

`core.py` works standalone without the GUI:

```bash
# Query current mode
.venv/bin/python core.py

# Set a mode
.venv/bin/python core.py integrated
.venv/bin/python core.py hybrid
.venv/bin/python core.py hybrid-rtd3
.venv/bin/python core.py nvidia

# Set hybrid-rtd3 with a specific RTD3 level (0–3, default 2)
.venv/bin/python core.py hybrid-rtd3 3
```

Switching modes requires `pkexec`. A reboot is needed for changes to take effect.

---

## Modes

| Mode | Description |
|------|-------------|
| `integrated` | Intel Iris Xe only. Best battery life. |
| `hybrid` | Both GPUs. Nvidia available via `prime-run <app>`. |
| `hybrid-rtd3` | Both GPUs. Nvidia auto powers off when idle. Recommended. |
| `nvidia` | Nvidia renders everything. No need for `prime-run`. |

## RTD3 levels (hybrid-rtd3 only)

| Value | Behavior |
|-------|----------|
| `0` | Disabled — Nvidia stays on |
| `1` | Coarse — off when no clients connected |
| `2` | Fine-grained — off even with idle clients (default) |
| `3` | Fine + VRAM self-refresh — most aggressive |

---

## File structure

```
GpuBatterySaver/
├── core.py                  # Headless core — importable or CLI
├── gui.py                   # PyQt6 GUI (imports core directly)
├── requirements.txt         # Runtime deps
├── requirements-build.txt   # Build deps (adds pyinstaller)
├── setup.sh                 # Local dev venv setup
├── build.sh                 # AppImage build
├── install.sh               # System install
├── uninstall.sh             # System uninstall
├── gpubatterysaver.desktop  # Desktop entry
└── assets/
    └── icon.svg
```

State (last mode + RTD3 level) is saved to `~/.config/gpubatterysaver/state.json`.
