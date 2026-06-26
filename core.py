import subprocess, sys, json, os
from pathlib import Path

STATE = Path.home() / ".config/gpubatterysaver/state.json"
AUTOSTART_FILE = Path.home() / ".config/autostart/gpubatterysaver.desktop"

MODES = ["integrated", "hybrid", "hybrid-rtd3", "nvidia"]

DEFAULT_COLORS = {
    "integrated":  "#4FC3F7",
    "hybrid":      "#81C784",
    "hybrid-rtd3": "#4CAF50",
    "nvidia":      "#76FF03",
}

def _load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {}

def _save_state(data: dict):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data))

def _boot_time() -> int:
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("btime"):
                    return int(line.split()[1])
    except Exception:
        pass
    return 0

def get_mode() -> str:
    r = subprocess.run(["envycontrol", "--query"], capture_output=True, text=True)
    base = r.stdout.strip()
    if base == "hybrid" and _load_state().get("mode") == "hybrid-rtd3":
        return "hybrid-rtd3"
    return base

def get_rtd3() -> int:
    return _load_state().get("rtd3", 2)

def has_pending_reboot() -> bool:
    state = _load_state()
    pb = state.get("pending_boot")
    return pb is not None and pb == _boot_time()

def set_mode(mode: str, rtd3: int = 2) -> bool:
    if mode not in MODES:
        return False
    cmd = ["envycontrol", "-s", "hybrid", "--rtd3", str(rtd3)] if mode == "hybrid-rtd3" \
        else ["envycontrol", "-s", mode.split("-")[0]]
    ok = subprocess.run(["pkexec"] + cmd).returncode == 0
    if ok:
        state = _load_state()
        state.update({"mode": mode, "rtd3": rtd3, "pending_boot": _boot_time()})
        _save_state(state)
    return ok

def get_colors() -> dict:
    return {**DEFAULT_COLORS, **_load_state().get("colors", {})}

def set_colors(colors: dict):
    state = _load_state()
    state["colors"] = colors
    _save_state(state)

def get_autostart() -> bool:
    return AUTOSTART_FILE.exists()

def set_autostart(enabled: bool):
    if enabled:
        AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
        if appimage := os.environ.get("APPIMAGE"):
            exec_line = f'"{appimage}"'
        else:
            gui = Path(__file__).resolve().parent / "gui.py"
            exec_line = f'"{sys.executable}" "{gui}"'
        AUTOSTART_FILE.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=GPU Battery Saver\n"
            f"Exec={exec_line}\n"
            "Icon=gpubatterysaver\n"
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
    else:
        AUTOSTART_FILE.unlink(missing_ok=True)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(get_mode())
    elif len(sys.argv) == 2:
        sys.exit(0 if set_mode(sys.argv[1]) else 1)
    elif len(sys.argv) == 3:
        sys.exit(0 if set_mode(sys.argv[1], int(sys.argv[2])) else 1)
