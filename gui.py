import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSystemTrayIcon, QMenu, QMessageBox, QTabWidget,
    QComboBox, QTextBrowser, QFrame, QCheckBox, QColorDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QAction
import core

MODES = ["integrated", "hybrid", "hybrid-rtd3", "nvidia"]

LABELS = {
    "integrated":  "Integrated — Intel Iris Xe only",
    "hybrid":      "Hybrid — Nvidia on demand",
    "hybrid-rtd3": "Hybrid + RTD3 — Nvidia auto-sleep",
    "nvidia":      "Nvidia only",
}

RTD3_OPTIONS = [
    (0, "0 — Disabled (Nvidia always on in hybrid)"),
    (1, "1 — Coarse (off when no clients connected)"),
    (2, "2 — Fine-grained (off even with clients)"),
    (3, "3 — Fine + VRAM self-refresh (most aggressive)"),
]

HELP_HTML = """
<h2>GPU Battery Saver</h2>
<p>Controls which GPU is active on your laptop via <b>envycontrol</b>.
Changes require a <b>reboot</b> to take effect.</p>

<hr>
<h3>Modes</h3>

<h4>Integrated — Intel Iris Xe only</h4>
<p>Disables the Nvidia GPU entirely. Only the Intel Iris Xe handles all rendering.
Best battery life. Use this for everyday tasks: browsing, coding, documents.</p>

<h4>Hybrid — Nvidia on demand</h4>
<p>Both GPUs are available. Intel handles everything by default.
Apps can request the Nvidia GPU explicitly using <code>prime-run &lt;app&gt;</code>.
Nvidia stays powered on but idle — some extra power draw even when unused.</p>

<h4>Hybrid + RTD3 — Nvidia auto-sleep</h4>
<p>Same as Hybrid, but the Nvidia GPU powers down automatically when idle.
Best balance: Nvidia available on demand, but saves power when not in use.
The RTD3 level (below) controls how aggressively it sleeps.</p>

<h4>Nvidia only</h4>
<p>All rendering goes through the Nvidia GPU. The Intel iGPU is still active
as a display bridge (since the screen is wired to it), but Nvidia does all the work.
Maximum performance, highest power draw. No need to use <code>prime-run</code>.</p>

<hr>
<h3>RTD3 Level (Hybrid + RTD3 only)</h3>
<p>Controls the <b>NVreg_DynamicPowerManagement</b> Nvidia kernel parameter.
Only applies when using the <i>Hybrid + RTD3</i> mode.</p>

<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; width:100%;">
  <tr><th>Value</th><th>Name</th><th>Behavior</th></tr>
  <tr><td><b>0</b></td><td>Disabled</td><td>No dynamic power management. Nvidia stays on.</td></tr>
  <tr><td><b>1</b></td><td>Coarse-grained</td><td>GPU powers off only when no application has it open.</td></tr>
  <tr><td><b>2</b></td><td>Fine-grained</td><td>GPU can power off even when an app has it open but isn't using it. Recommended.</td></tr>
  <tr><td><b>3</b></td><td>Fine + VRAM self-refresh</td><td>Same as fine-grained, but also suspends video memory. Most power savings, slightly more wake latency.</td></tr>
</table>

<hr>
<h3>System tray</h3>
<p>The colored dot in your system tray shows the current mode at a glance.
Left-click to show/hide the window. Right-click for a quick-switch menu.</p>
<p>The dot turns <b style="color:#FF3D00">red</b> when a mode change is pending reboot.</p>

<h3>State file</h3>
<p>The app saves your last mode, RTD3 setting, and custom colors to
<code>~/.config/gpubatterysaver/state.json</code>.
This lets it distinguish <i>Hybrid</i> from <i>Hybrid + RTD3</i> across reboots
(both look the same to envycontrol's <code>--query</code>).</p>
"""


def _circle_icon(color: str, size: int = 22) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.end()
    return QIcon(pix)


class _SwitchWorker(QThread):
    done = pyqtSignal(bool)

    def __init__(self, mode: str, rtd3: int):
        super().__init__()
        self.mode = mode
        self.rtd3 = rtd3

    def run(self):
        self.done.emit(core.set_mode(self.mode, self.rtd3))


class ModesTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._win = parent
        self._selected: str | None = None
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        self.status = QLabel()
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("font-size: 12px; color: #888; margin-bottom: 4px;")
        layout.addWidget(self.status)

        self.buttons: dict[str, QPushButton] = {}
        for mode in MODES:
            btn = QPushButton(LABELS[mode])
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda _, m=mode: self._select(m))
            layout.addWidget(btn)
            self.buttons[mode] = btn

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")
        layout.addWidget(sep)

        rtd3_row = QHBoxLayout()
        rtd3_label = QLabel("RTD3 level:")
        rtd3_label.setStyleSheet("font-size: 11px;")
        rtd3_row.addWidget(rtd3_label)

        self.rtd3_box = QComboBox()
        for val, desc in RTD3_OPTIONS:
            self.rtd3_box.addItem(desc, val)
        self.rtd3_box.setCurrentIndex(core.get_rtd3())
        rtd3_row.addWidget(self.rtd3_box, 1)
        layout.addLayout(rtd3_row)

        note = QLabel("RTD3 applies only to Hybrid + RTD3 mode.")
        note.setStyleSheet("font-size: 10px; color: #777;")
        layout.addWidget(note)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #444;")
        layout.addWidget(sep2)

        self.switch_btn = QPushButton("Switch")
        self.switch_btn.setMinimumHeight(40)
        self.switch_btn.setEnabled(False)
        self.switch_btn.clicked.connect(self._do_switch)
        layout.addWidget(self.switch_btn)

    def _select(self, mode: str):
        self._selected = mode
        self._refresh_styles()
        self.switch_btn.setEnabled(mode != self._win._current)

    def _do_switch(self):
        if self._selected and self._selected != self._win._current:
            self._win.switch(self._selected)

    def _refresh_styles(self):
        current = self._win._current
        colors = core.get_colors()
        for mode, btn in self.buttons.items():
            color = colors.get(mode, "#888")
            if mode == current:
                btn.setStyleSheet(f"background:{color}; color:#000; font-weight:bold;")
            elif mode == self._selected:
                btn.setStyleSheet(
                    f"border: 2px solid {color}; color: {color}; font-weight: bold;"
                )
            else:
                btn.setStyleSheet("")

    def rtd3_value(self) -> int:
        return self.rtd3_box.currentData()

    def refresh(self, current: str):
        if self._selected is None:
            self._selected = current
        self.status.setText(f"Current: {LABELS.get(current, current)}")
        self._refresh_styles()
        self.switch_btn.setEnabled(self._selected != current)

    def reset_selection(self):
        self._selected = self._win._current
        self._refresh_styles()
        self.switch_btn.setEnabled(False)

    def set_enabled(self, enabled: bool):
        for btn in self.buttons.values():
            btn.setEnabled(enabled)
        self.rtd3_box.setEnabled(enabled)
        self.switch_btn.setEnabled(
            enabled
            and self._selected is not None
            and self._selected != self._win._current
        )


class SettingsTab(QWidget):
    colors_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        self._autostart = QCheckBox("Start app at login")
        self._autostart.setChecked(core.get_autostart())
        self._autostart.toggled.connect(core.set_autostart)
        layout.addWidget(self._autostart)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")
        layout.addWidget(sep)

        layout.addWidget(QLabel("Mode Colors:"))

        self._swatches: dict[str, QPushButton] = {}
        colors = core.get_colors()
        for mode in MODES:
            row = QHBoxLayout()
            lbl = QLabel(LABELS[mode].split(" — ")[0])
            lbl.setMinimumWidth(150)
            row.addWidget(lbl)
            btn = QPushButton()
            btn.setFixedSize(80, 24)
            btn.setStyleSheet(f"background: {colors[mode]}; border: 1px solid #555;")
            btn.clicked.connect(lambda _, m=mode: self._pick_color(m))
            row.addWidget(btn)
            row.addStretch()
            self._swatches[mode] = btn
            layout.addLayout(row)

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addStretch()

    def _pick_color(self, mode: str):
        colors = core.get_colors()
        chosen = QColorDialog.getColor(QColor(colors[mode]), self, f"Color for {mode}")
        if chosen.isValid():
            colors[mode] = chosen.name()
            core.set_colors(colors)
            self._swatches[mode].setStyleSheet(
                f"background: {chosen.name()}; border: 1px solid #555;"
            )
            self.colors_changed.emit()

    def _reset(self):
        core.set_colors({})
        colors = core.get_colors()
        for mode, btn in self._swatches.items():
            btn.setStyleSheet(f"background: {colors[mode]}; border: 1px solid #555;")
        self.colors_changed.emit()


class HelpTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        browser = QTextBrowser()
        browser.setHtml(HELP_HTML)
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPU Battery Saver")
        self.setMinimumWidth(400)
        self._worker = None
        self._switching = False
        self._current = core.get_mode()
        self._build_ui()
        self._build_tray()
        self._refresh()
        self.tray.show()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._warn = QLabel("Reboot pending — mode change not yet active")
        self._warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warn.setStyleSheet(
            "background: #FFD600; color: #111; font-weight: bold; padding: 6px;"
        )
        self._warn.hide()
        layout.addWidget(self._warn)

        tabs = QTabWidget()
        self.modes_tab = ModesTab(self)
        self._settings_tab = SettingsTab()
        self._settings_tab.colors_changed.connect(self._refresh)
        tabs.addTab(self.modes_tab, "Modes")
        tabs.addTab(self._settings_tab, "Settings")
        tabs.addTab(HelpTab(), "Help")
        layout.addWidget(tabs)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        menu = QMenu()
        for mode in MODES:
            act = QAction(LABELS[mode], self)
            act.triggered.connect(lambda _, m=mode: self.switch(m))
            menu.addAction(act)
        menu.addSeparator()
        menu.addAction("Show", self.show)
        self._quit_action = QAction("Quit", self)
        self._quit_action.triggered.connect(QApplication.quit)
        menu.addAction(self._quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show() if self.isHidden() else self.hide()

    def _refresh(self):
        pending = core.has_pending_reboot()
        self._warn.setVisible(pending)
        colors = core.get_colors()
        tray_color = "#FF3D00" if pending else colors.get(self._current, "#888")
        self.modes_tab.refresh(self._current)
        self.tray.setIcon(_circle_icon(tray_color))
        tooltip = f"GPU: {LABELS.get(self._current, self._current)}"
        if pending:
            tooltip += " (reboot pending)"
        self.tray.setToolTip(tooltip)

    def switch(self, mode: str):
        if mode == self._current:
            return
        self._switching = True
        self._quit_action.setEnabled(False)
        self.modes_tab.set_enabled(False)
        self.modes_tab.status.setText("Rebuilding initramfs… do not close")
        rtd3 = self.modes_tab.rtd3_value()
        self._worker = _SwitchWorker(mode, rtd3)
        self._worker.done.connect(lambda ok: self._on_done(ok, mode))
        self._worker.start()

    def _on_done(self, ok: bool, mode: str):
        self._switching = False
        self._quit_action.setEnabled(True)
        self.modes_tab.set_enabled(True)
        if ok:
            self._current = mode
            self.modes_tab.reset_selection()
            self._refresh()
            QMessageBox.information(
                self, "Reboot required",
                f"Switched to:\n{LABELS[mode]}\n\nPlease reboot for changes to take effect.",
            )
        else:
            self._refresh()
            QMessageBox.critical(self, "Error",
                "Failed to switch GPU mode.\nCheck that envycontrol is installed.")
        self._worker = None

    def closeEvent(self, event):
        event.ignore()
        if not self._switching:
            self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    if "--tray-only" not in sys.argv:
        win.show()
    sys.exit(app.exec())
